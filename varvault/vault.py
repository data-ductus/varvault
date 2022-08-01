from __future__ import annotations

import asyncio
import logging
import functools
import traceback

from typing import *
from threading import Lock

from .filehandlers import BaseFileHandler, ResourceNotFoundError
from .keyring import Keyring, Key
from .logger import get_logger, configure_logger
from .minivault import MiniVault
from .utils import concurrent_execution, create_mini_vault_from_file
from .vaultflags import VaultFlags


class VarVault(object):
    class Vault(dict):
        def __init__(self, vault_filehandler: BaseFileHandler = None, vault_is_read_only=False, live_update=False):
            super(VarVault.Vault, self).__init__()
            self.writable_args = dict()
            self.vault_is_read_only = vault_is_read_only
            self.live_update = live_update
            self.filehandler = vault_filehandler

        def __setitem__(self, key, value):
            data = {key: value}
            if self.filehandler and self.filehandler.kv_pair_can_be_written(data):
                self.writable_args.update(data)

            super(VarVault.Vault, self).__setitem__(key, value)

        @functools.singledispatchmethod
        def put(self, *args, **kwargs):
            raise NotImplementedError("Not implemented")

        @put.register
        def _mv(self, mini: MiniVault):
            f"""{self.put} to add a MiniVault"""

            async def _put(item):
                key, value = item
                self.__setitem__(key, value)
            concurrent_execution(_put, mini.items())
            self.write()

        @put.register
        def _k_v(self, key: Key, value: object):
            f"""{self.put} to add a key-value pair"""
            self.__setitem__(key, value)
            self.write()

        def write(self):
            # If the vault file is set to read-only, don't write to it.
            if self.vault_is_read_only:
                return

            # No filehandler has been defined, which means we cannot write anything to the file
            if not self.filehandler:
                return

            # Try to write writable_args to vault_file if it has been defined
            self.filehandler.write(self.writable_args)

    def __init__(self,
                 varvault_keyring: Type[Keyring],
                 varvault_vault_name: str,
                 *flags: VaultFlags,
                 varvault_filehandler_from: BaseFileHandler = None,
                 varvault_filehandler_to: BaseFileHandler = None,
                 varvault_specific_logger: logging.Logger = None,
                 **extra_keys):
        f"""
        Creates a vault-object. You should ideally create a vault from the existing factory functions. 
        
        :param varvault_keyring: The {Keyring} class used for this vault.  
        :param varvault_vault_name: The name of the vault. This is used when creating a logfile for logging information to. 
        :param flags: A set of flags used to tweak the behavior of the vault object. See {VaultFlags} for what flags can be used and what they do.   
        :param varvault_filehandler_from: Optional. The name of the file to load a vault from.  
        :param varvault_filehandler_to: Optional. The name of a file to write data in the vault to.
        :param varvault_specific_logger: Optional. A specific logger to log to in-case you do not want to use the built-in logger in varvault.  
        :param extra_keys: Optional. A kwargs-object with extra keys that are not defined in the {varvault_keyring}. This can be useful when you have a lot of keys that you might 
         want to handle in a programmatic sense rather than in a pre-defined sense. 
        """
        assert issubclass(varvault_keyring, Keyring), f"'keyring' must be a subclass of {Keyring}"
        assert varvault_filehandler_from is None or isinstance(varvault_filehandler_from, BaseFileHandler), f"'varvault_filehandler_from' must be of type {BaseFileHandler}, or {None}, not {type(varvault_filehandler_from)}"
        assert varvault_filehandler_to is None or isinstance(varvault_filehandler_to, BaseFileHandler), f"'varvault_filehandler_to' must be of type {BaseFileHandler}, or {None}, not {type(varvault_filehandler_to)}"
        assert not VaultFlags.flag_is_set(VaultFlags.clean_return_keys(), *flags), f"You really should not set {VaultFlags.clean_return_keys()} " \
                                                                                   f"to the vault itself as that would be an extremely bad idea."
        for key_name, key in extra_keys.items():
            assert isinstance(key_name, str) and isinstance(key, Key), f"extra_keys is not setup correctly; The pattern {{{key_name} ({type(key_name)}): {key} ({type(key)})}} is incorrect. Correct pattern would be {{{key_name} ({str}): {key} ({Key})}}"

        disable_logger = VaultFlags.flag_is_set(VaultFlags.disable_logger(), *flags)
        remove_existing_log_file = VaultFlags.flag_is_set(VaultFlags.remove_existing_log_file(), *flags)
        self.keyring_class = varvault_keyring
        self.flags: list = list(flags)
        self.vault_is_read_only = VaultFlags.flag_is_set(VaultFlags.vault_is_read_only(), *self.flags)
        self.live_update = VaultFlags.flag_is_set(VaultFlags.live_update(), *self.flags)
        self.filehandler_from: BaseFileHandler = varvault_filehandler_from
        self.filehandler_to: BaseFileHandler = varvault_filehandler_to

        if varvault_specific_logger:
            self.logger = varvault_specific_logger
        else:
            self.logger = get_logger(varvault_vault_name, remove_existing_log_file) if not disable_logger else None

        self.lock = Lock()

        # Get the keys from the keyring and expand it with extra keys
        self.keys: Dict[str, Key] = self.keyring_class.get_keys_in_keyring()
        self.keys.update(extra_keys)

        # Create the inner vault
        self.inner_vault = self.Vault(varvault_filehandler_to, vault_is_read_only=self.vault_is_read_only, live_update=self.live_update)
        self.vault_file_from_hash = self._get_vault_file_hash()

        if self.filehandler_to:
            self.log(f"Vault writing data to '{self.filehandler_to.path}'", level=logging.INFO)
        if self.live_update:
            self.log(f"Vault doing live updates from '{self.filehandler_from.path}' whenever the vault is accessed.", level=logging.INFO)

    def __contains__(self, key: Key):
        self._assert_key_is_correct_type(key, msg=f"{self.__contains__.__name__} may only be used with a {Key}-object, not {type(key)}")

        if key.key_name not in self.keys:
            self.log(f"Key {key} does not exist in the keyring. Trying to check if the vault contains this key will never succeed; Consider removing the call that triggered this warning.", level=logging.WARNING)
            return False

        return key in self.vault

    def __str__(self):
        return self.inner_vault.__str__()
    
    def log(self, msg: object, *args, level: int = logging.DEBUG, exception: BaseException = None):
        assert isinstance(level, int), "Log level must be defined as an integer"
        if self.logger:
            self.logger.log(level, msg, *args, exc_info=exception)

    @property
    def vault(self) -> Vault:
        return self.inner_vault

    # =========================================================================================================================================
    # vaulter
    # =========================================================================================================================================
    def vaulter(self, *flags: VaultFlags, input_keys: Union[Key, list, tuple] = None, return_keys: Union[Key, list, tuple] = None) -> Callable:
        f"""
        Decorator to define a function as a vaulted function.
        A vaulted function works a lot different to a normal function.
        A vault works like a key-value storage. A vaulted function will get its arguments
        by accessing them from the vault, and then store any returned value back in the vault.

        :param input_keys: Can be of type: {Key}, {list}, {tuple}. Default: {None}. Keys must be defined in the
         keyring for this specific vault.
        :param return_keys: Can be of type: {str}, {list}, {tuple}. Default: {None}. Keys must be defined in the
         keyring for this specific vault.
        :param flags: Optional argument for defining some flags for this vaulted function. Flags that have an effect:
         {VaultFlags.debug},
         {VaultFlags.silent},
         {VaultFlags.input_key_can_be_missing},
         {VaultFlags.permit_modifications},
         {VaultFlags.split_return_keys},
         {VaultFlags.return_key_can_be_missing},
         {VaultFlags.clean_return_keys},
         {VaultFlags.no_error_logging}
        """
        input_keys = input_keys if input_keys else list()
        return_keys = return_keys if return_keys else list()
        all_flags = self._get_all_flags(*flags)
        # Validate the input to the decorator
        self._vaulter__validate_input(input_keys, return_keys)

        # Convert input- and return keys to a list if it's a single key to make it easier to handle
        input_keys, return_keys = self._vaulter__convert_input_keys_and_return_keys(input_keys, return_keys)

        # Assert that the keys are in the keyring
        self._vaulter__assert_keys_in_keyring(input_keys, return_keys)

        def wrap_outer(func):
            func_module_name = f"{func.__module__}.{func.__name__}"

            def pre_call(**kwargs):
                self._try_reload_from_file()
                input_kwargs = self._vaulter__build_input_var_keys(input_keys, kwargs, *all_flags)
                kwargs.update(input_kwargs)
                self._configure_log_levels_based_on_flags(*all_flags)
                assert callable(func)

                self.log(f"======{'=' * len(func_module_name)}=")
                self.log(f">>>>> {func_module_name}:")
                if input_kwargs:
                    self.log(f"-------------")
                    self.log(f"Input kwargs:")
                    for kwarg_key, kwarg_value in input_kwargs.items():
                        self.log(f"{kwarg_key}: ({type(kwarg_value)}) -- {kwarg_value}")
                    self.log(f"-------------")

                input_kwargs.update(kwargs)

                self.log(f"======= Calling {func_module_name} ========")
                return input_kwargs

            def post_call(ret):
                self._configure_log_levels_based_on_flags(*all_flags)
                self._vaulter__handle_return_vars(ret, return_keys, *all_flags)
                self._configure_log_levels_based_on_flags(*all_flags)
                self.log(f"<<<<< {func_module_name}:")
                self.log(f"======{'=' * len(func_module_name)}=\n")
                self._reset_log_levels()

            # Separate handling if the decorated function uses the coroutine API
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def wrap_inner_async(*args, **kwargs):
                    #
                    # Do pre-call related stuff
                    #
                    input_kwargs = pre_call(**kwargs)
                    try:
                        ret = await func(*args, **input_kwargs)
                    except Exception as e:
                        self.log(f"Failed to run {func_module_name}: {e}", level=logging.ERROR)
                        self.log(str(traceback.format_exc()).rstrip("\n"), level=logging.ERROR)
                        raise

                    #
                    # Do post-call related stuff
                    #
                    post_call(ret)

                    return ret
                return wrap_inner_async
            else:
                @functools.wraps(func)
                def wrap_inner(*args, **kwargs):
                    #
                    # Do pre-call related stuff
                    #
                    input_kwargs = pre_call(**kwargs)
                    try:
                        ret = func(*args, **input_kwargs)
                    except Exception as e:
                        if not VaultFlags.flag_is_set(VaultFlags.no_error_logging(), *all_flags):
                            # Flag to not log error is NOT set, so we should log the error and then raise the error
                            self.log(f"Failed to run {func_module_name}: {e}", level=logging.ERROR)
                            self.log(str(traceback.format_exc()).rstrip("\n"), level=logging.ERROR)
                        raise

                    #
                    # Do post-call related stuff
                    #
                    post_call(ret)

                    return ret
                return wrap_inner
        return wrap_outer

    def _vaulter__validate_input(self, input_keys, return_keys, *flags):
        assert isinstance(input_keys, (Key, list, tuple)), f"input_keys must be of type {Key}, {list}, or {tuple}"
        assert isinstance(return_keys, (Key, list, tuple)), f"return_keys must be of type {Key}, {list}, or {tuple}"

        for flag in flags:
            assert isinstance(flag, VaultFlags), f"Flag must be of type {VaultFlags}, not '{type(flag)}'"

    def _vaulter__convert_input_keys_and_return_keys(self, input_keys, return_keys):
        if isinstance(input_keys, Key):
            input_keys = [input_keys]
        if isinstance(return_keys, Key):
            return_keys = [return_keys]

        assert isinstance(input_keys, (list, tuple)), f"Input keys doesn't have the correct type; actual type: {type(input_keys)}"
        assert isinstance(return_keys, (list, tuple)), f"Return keys doesn't have the correct type; actual type: {type(input_keys)}"
        return input_keys, return_keys

    def _vaulter__assert_keys_in_keyring(self, input_keys, return_keys):
        for key in input_keys:
            self._assert_key_is_correct_type(key)
            assert key in self.keys, f"Key '{key}' isn't defined as a key in the keyring"

        for key in return_keys:
            self._assert_key_is_correct_type(key)
            assert key in self.keys, f"Key '{key}' isn't defined as a key in the keyring"

    def _vaulter__build_input_var_keys(self, input_keys, kwargs, *flags):
        mini = self.get_multiple(input_keys, *flags)

        assert len(input_keys) == len(mini) or VaultFlags.flag_is_set(VaultFlags.input_key_can_be_missing(), *flags), \
            f"The number of items acquired from {self.get_multiple.__name__} is not the same as the number of input-keys to the method, " \
            f"and {VaultFlags.input_key_can_be_missing()} is not set. This is probably a bug."

        for key, value in mini.items():
            assert key not in kwargs, f"Key {key} seems to already exist in kwargs used for the function decorated with '@{self.vaulter.__name__}'"

        return mini

    def _vaulter__handle_return_vars(self, ret, return_keys, *flags):

        if not return_keys:
            # No return keys were defined; Just return from here then as there is nothing else to do.
            return

        all_flags = self._get_all_flags(*flags)

        if VaultFlags.flag_is_set(VaultFlags.split_return_keys(), *all_flags):
            assert isinstance(ret, MiniVault), f"If {VaultFlags.split_return_keys()} is defined, you MUST return values in the form of a {MiniVault} object or we cannot determine which keys go where"
            ret = MiniVault({key: value for key, value in ret.items() if key in return_keys})
        if VaultFlags.flag_is_set(VaultFlags.return_key_can_be_missing(), *all_flags):
            assert isinstance(ret, MiniVault), f"If {VaultFlags.return_key_can_be_missing()} is defined, you MUST return values in the form of a {MiniVault} object or we " \
                                               f"cannot determine which keys should be assigned to the vault and which should be skipped."
        if VaultFlags.flag_is_set(VaultFlags.clean_return_keys(), *all_flags):
            self._clean_return_keys(return_keys)
        else:
            mini = self._to_minivault(return_keys, ret, *flags)

            async def validate_keys_in_mini_vault(key, can_be_missing=False):
                assert key in mini or can_be_missing, f"Key {key} isn't present in MiniVault; keys in mini: {mini.keys()}. " \
                                                      f"You can set the vault-flag {VaultFlags.return_key_can_be_missing()} to skip this validation step"
            concurrent_execution(validate_keys_in_mini_vault, return_keys, can_be_missing=VaultFlags.flag_is_set(VaultFlags.return_key_can_be_missing(), *all_flags))

            async def validate_keys_in_return_keys(key):
                assert key in return_keys, f"Key {key} isn't defined as a return-key; return keys: {return_keys}"
            concurrent_execution(validate_keys_in_return_keys, mini.keys())

            self.insert_minivault(mini, *flags)

    # ============================================================
    # insert
    # ============================================================
    def insert(self, key: Key, value: object, *flags: VaultFlags):
        f"""
        Inserts a {value} into the vault mapped to {key}.
        
        :param key: The {key} to insert the value to. Type must be {Key} 
        :param value: The object to assign to {key}
        :param flags: An optional set of flags to tweak the behavior of the insert. Flags that have an effect: 
         {VaultFlags.permit_modifications},
         {VaultFlags.return_values_cannot_be_none}, 
         {VaultFlags.debug},
         {VaultFlags.silent}
        """
        # Key must be as an iterable, but value doesn't have to be
        mini = self._to_minivault([key], value, *self._get_all_flags(*flags))
        self.insert_minivault(mini, *self._get_all_flags(*flags))

    # ==================================================
    # insert_minivault
    # ==================================================
    def insert_minivault(self, mini: MiniVault, *flags):
        f"""
        Inserts a {MiniVault} into the vault.
        
        :param mini: The {MiniVault} to insert into the vault. 
        :param flags: An optional set of flags to tweak the behavior of the insert. Flags that have an effect: 
         {VaultFlags.permit_modifications},
         {VaultFlags.return_values_cannot_be_none}, 
         {VaultFlags.debug},
         {VaultFlags.silent}
        """
        all_flags = self._get_all_flags(*flags)

        # Assert that key has correct type
        for key in mini.keys():
            self._assert_key_is_correct_type(key)
        self._configure_log_levels_based_on_flags(*all_flags)

        async def assert_key_and_value_may_be_inserted(key, value):
            if VaultFlags.flag_is_set(VaultFlags.return_values_cannot_be_none(), *all_flags):
                assert value is not None, f"The value mapped to {key} is {None} and {VaultFlags.return_values_cannot_be_none()} is defined."

            self._insert__assert_key_in_keyring(key)
            self._insert__assert_value_may_be_inserted(key, value, modifications_permitted=VaultFlags.flag_is_set(VaultFlags.permit_modifications(), *all_flags))
        concurrent_execution(assert_key_and_value_may_be_inserted, mini.keys(), mini.values())

        with self.lock:
            self.log("-------------------")
            self.log("Variables going in:")
            for ret_key, ret_value in mini.items():
                self.log(f"{ret_key}: ({type(ret_value)}) -- {ret_value}")
            self.vault.put(mini)
            self.log("-----------------")
        self._reset_log_levels()

    def _insert__assert_key_in_keyring(self, key: Key):
        """Assert that the key is in the keyring"""
        assert key in self.keys

    def _insert__assert_value_may_be_inserted(self, key: Key, value: object, modifications_permitted=False):
        # Validate that key doesn't already exist in the vault, or that modifications_permitted==True
        assert key not in self or modifications_permitted, f"Key {key} already exists in the vault and modifications to existing variables are not permitted."

        # Validate the type of the value to insert into the vault
        assert key.type_is_valid(value), f"Key '{key}' requires type to be '{key.valid_type}', but type for value is '{type(value)}'."

    # ========================================================
    # get
    # ========================================================
    def get(self, key: Key, *flags: VaultFlags, default=None):
        f"""
        Get an object from the vault that is mapped to {key}. 
        
        :param key: The key to get an object for. Must be of type {Key}
        :param flags: An optional set of flags to tweak the behavior of the get. Flags that have an effect:
         {VaultFlags.debug},
         {VaultFlags.silent},
         {VaultFlags.input_key_can_be_missing}
        :param default: An optional argument to define which value to return as default is the value doesn't exist in the vault. Default is {None}. Only applicable if {VaultFlags.input_key_can_be_missing()} is set.
        :return: The object in the vault mapped to the {key}, or {None} if it's not in the vault.  
        """
        mv = self.get_multiple([key], *flags)
        if VaultFlags.flag_is_set(VaultFlags.input_key_can_be_missing(), *flags):
            return mv.get(key, default)
        return mv.get(key)

    # =======================================================================
    # get_multiple
    # =======================================================================
    def get_multiple(self, keys: List[Key], *flags: VaultFlags) -> MiniVault:
        f"""
        Get multiple objects from the vault that are mapped to keys in {keys}. 
        
        :param keys: A list of keys to get the objects for. Must be a list of {Key} objects
        :param flags: An optional set of flags to tweak the behavior of the get. Flags that have an effect:
         {VaultFlags.debug},
         {VaultFlags.silent},
         {VaultFlags.input_key_can_be_missing}
        :return: A {MiniVault} with all the objects in the vault mapped to the keys, or {None} if it's not in the vault.  
        """

        all_flags = self._get_all_flags(*flags)
        mini = MiniVault()
        for key in keys:
            self._assert_key_is_correct_type(key)
        with self.lock:
            self._try_reload_from_file()

            self._configure_log_levels_based_on_flags(*all_flags)
            if not VaultFlags.flag_is_set(VaultFlags.input_key_can_be_missing(), *all_flags):
                for key in keys:
                    assert key in self, f"Key {key} is not mapped to an object in the vault; it appears to be missing in the vault. " \
                                        f"You can set the flag '{VaultFlags.input_key_can_be_missing()}' to avoid this, " \
                                        f"in which case the value will be {None}, or make sure a value is mapped to it."
            [mini.update({key: self.vault.get(key)}) for key in keys if key in self]
            self._reset_log_levels()
        return mini

    def _assert_key_is_correct_type(self, key: Key, can_be_str=False, msg=None):
        # Define the error message based on input
        if not msg:
            if can_be_str:
                msg = f"Key {key} is not of required type {Key} or {str}"
            else:
                msg = f"Key {key} is not of required type {Key}"

        if can_be_str:
            assert isinstance(key, (Key, str)), msg
        else:
            assert isinstance(key, Key), msg

    def _try_reload_from_file(self):
        """Can be used to reload from a file if changes has been made to it before"""
        if self.filehandler_from and self.live_update:
            if not self.filehandler_from.resource:
                self.filehandler_from.create_resource(self.filehandler_from.path)
            current_hash = self._get_vault_file_hash()

            # If current hash is an empty string, that means no hash was able to be acquired. In this case, there is no file to load from; Raise FileNotFoundError
            if current_hash == "":
                raise ResourceNotFoundError(f"Failed to read from resource {self.filehandler_from.path} to get the current "
                                            f"contents of it to perform live updates. This means you've created a vault "
                                            f"from a file that doesn't exist and set it to perform live updates, but you "
                                            f"tried to read from the vault-file before the vault-file was created. This "
                                            f"is simply not permitted and you will have to look at your workflow to "
                                            f"figure out an appropriate solution for this problem. ", self.filehandler_from)

            if current_hash != self.vault_file_from_hash:
                mini = create_mini_vault_from_file(self.filehandler_from, self.keyring_class)
                self.vault_file_from_hash = current_hash
                self.vault.put(mini)

    def _get_vault_file_hash(self):
        if not self.filehandler_from:
            return ""
        else:
            try:
                return self.filehandler_from.hash()
            except (ResourceNotFoundError, FileNotFoundError) as e:
                if self.live_update:
                    # This is fine; It just means the file doesn't exist yet
                    return ""
                else:
                    raise e

    def _get_all_flags(self, *flags):
        all_flags = self.flags.copy()
        all_flags.extend(flags)
        return all_flags

    def _configure_log_levels_based_on_flags(self, *all_flags):
        if not self.logger:
            # No logger has been assigned for this vault. Just return then.
            return
        if VaultFlags.flag_is_set(VaultFlags.silent(), *all_flags) and VaultFlags.flag_is_set(VaultFlags.debug(), *all_flags):
            # Use default logging levels; debug and silent cancel each other out
            configure_logger(self.logger)
        elif VaultFlags.flag_is_set(VaultFlags.silent(), *all_flags):
            configure_logger(self.logger, overall_level=logging.INFO)
        elif VaultFlags.flag_is_set(VaultFlags.debug(), *all_flags):
            configure_logger(self.logger, stream_level=logging.DEBUG)

    def _reset_log_levels(self):
        if not self.logger:
            # No logger has been assigned for this vault. Just return then.
            return
        configure_logger(self.logger, overall_level=logging.DEBUG, stream_level=logging.INFO, file_level=logging.DEBUG)

    def _clean_return_keys(self, return_keys: Union[List[Key], Tuple[Key]]):
        self.log(f"Cleaning return var keys: {return_keys}")
        for key in return_keys:
            if not key.valid_type:
                temp = None
                self.log(f"Cleaning key {key} by setting it to None (no valid_type defined for {key})")
            else:
                try:
                    temp = key.valid_type()
                    self.log(f"Cleaning key {key} by setting it to '{temp}' (key.valid_type = {key.valid_type})")
                except:
                    temp = None
                    self.log(f"Cleaning key {key} by setting it to '{None}' (valid_type is defined, but no default constructor appears to exist for {key.valid_type})")
            self.vault.put(key, temp)

    def _to_minivault(self, return_keys, ret, *flags) -> MiniVault:
        all_flags = self._get_all_flags(*flags)
        if isinstance(ret, MiniVault):
            mini = ret
        else:
            # It's not a MiniVault; Let's turn it into one.
            if isinstance(ret, tuple):
                # It's a tuple, which means it's either meant as a single item, or there are multiple return objects
                if len(return_keys) == 1:
                    # There's only one return key defined, which means the keys valid type should be tuple, OR the flag return_tuple_is_single_item is set
                    assert return_keys[0].valid_type == tuple or VaultFlags.flag_is_set(VaultFlags.return_tuple_is_single_item(), *all_flags), \
                        f"You have defined only a single return key, yet you are returning multiple items, while the valid type for key " \
                        f"{self.keyring_class.__name__}.{return_keys[0]} is not {tuple}, nor is {VaultFlags.return_tuple_is_single_item()} set."

                    mini = MiniVault.build(return_keys, [ret])
                else:
                    assert len(return_keys) == len(ret), "The number of return variables and the number of return keys must be identical in order to map the keys to the return variables"
                    mini = MiniVault.build(return_keys, ret)
            else:
                # ret is a single item
                assert len(return_keys) == 1, "There appear to be more than 1 return-key defined, but only a single item that is returned"
                mini = MiniVault.build(return_keys, [ret])
        return mini
