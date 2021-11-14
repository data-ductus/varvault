from __future__ import annotations

import asyncio
import os
import _io
import json
import logging
import functools
import traceback

from typing import *
from threading import Lock

from .minivault import MiniVault
from .keyring import Keyring, Key
from .utils import concurrent_execution, md5hash, create_return_vault_from_file, is_serializable
from .vaultflags import VaultFlags
from .logger import get_logger, configure_logger


class VarVault(object):
    class Vault(dict):
        def __init__(self, vault_file: TextIO = None):
            super(VarVault.Vault, self).__init__()
            self.writable_args = dict()
            self.vault_file = vault_file

        def __setitem__(self, key, value):
            data = {key: value}
            if is_serializable(data):
                self.writable_args.update(data)

            super(VarVault.Vault, self).__setitem__(key, value)

        @functools.singledispatchmethod
        def put(self, *args, **kwargs):
            raise NotImplementedError("Not implemented")

        @put.register
        def _mv(self, mini: MiniVault):
            async def _put(item):
                key, value = item
                self.__setitem__(key, value)
            concurrent_execution(_put, mini.items())
            self.write()

        @put.register
        def _k_v(self, key: Key, value: object):
            self.__setitem__(key, value)
            self.write()

        def write(self):
            # Try to write writable_args to vault_file if it has been defined
            if self.vault_file:
                json.dump(self.writable_args, open(self.vault_file.name, "w"), indent=2)

    def __init__(self, keyring: Type[Keyring], name: str,
                 *flags: VaultFlags,
                 use_logger: bool = True,
                 vault_filename_from: str = None,
                 vault_filename_to: str = None,
                 file_is_read_only: bool = False,
                 remove_existing_log_file: bool = False,
                 **extra_keys):
        assert issubclass(keyring, Keyring), f"'keyring' must be a subclass of {Keyring}"
        self.keyring_class = keyring
        self.logger = get_logger(name, remove_existing_log_file) if use_logger else None 
        self.flags: list = list(flags)
        self.lock = Lock()
        assert not VaultFlags.flag_is_set(VaultFlags.clean_return_var_keys(), *self.flags), f"You really should not set {VaultFlags.clean_return_var_keys()} " \
                                                                                            f"to the vault itself as that would be an extremely bad idea."

        # Get the keys from the keyring and expand it with extra keys
        self.keys: Dict[str, Key] = self.keyring_class.get_keys_in_keyring()
        for key_name, key in extra_keys.items():
            assert isinstance(key_name, str) and isinstance(key, Key), f"extra_keys is not setup correctly; The pattern {{{key_name} ({type(key_name)}): {key} ({type(key)})}} is incorrect. Correct pattern would be {{{key_name} ({str}): {key} ({Key})}}"
        self.keys.update(extra_keys)

        # Expand vault-files passed to constructor to expand both env vars and user in case they have been defined that way
        vault_filename_from = os.path.expanduser(os.path.expandvars(vault_filename_from)) if vault_filename_from else None
        vault_filename_to = os.path.expanduser(os.path.expandvars(vault_filename_to)) if vault_filename_to else None
        self.vault_filename_from = vault_filename_from
        self.vault_filename_to = vault_filename_to

        self.file_is_read_only = file_is_read_only

        # Create the vault file object
        self.vault_file = self._create_vault_file() if self.vault_filename_to and not self.file_is_read_only else None
        self.live_update = VaultFlags.flag_is_set(VaultFlags.live_update(), *self.flags)

        self.vault_file_from_hash = self._get_vault_file_hash()

        # Create the inner vault
        self.inner_vault = self.Vault(self.vault_file)

        if self.vault_file:
            self.log(f"Vault writing data to '{self.vault_file.name}'", level=logging.INFO)
        if self.live_update:
            self.log(f"Vault doing live updates from '{self.vault_filename_from}' whenever the vault is accessed.", level=logging.INFO)

    def __eq__(self, other):
        pass

    def __contains__(self, key: Key):
        self._assert_key_is_correct_type(key, msg=f"{self.__contains__.__name__} may only be used with a {Key}-object, not {type(key)}")

        if key.key_name not in self.keys:
            self.log(f"Key {key} does not exist in the keyring. Trying to check if the vault contains this key will never succeed; Consider removing the call that triggered this warning.", level=logging.WARNING)
            return False

        return key in self.vault

    def __del__(self):
        # Close database_file if it has been defined
        if self.vault_file and isinstance(self.vault_file, _io.TextIOWrapper):
            self.vault_file.close()

    def __copy__(self):
        pass
    
    def log(self, msg: object, *args, level=logging.DEBUG, exception: BaseException = None):
        assert isinstance(level, int), "Log level must be defined as an integer"
        if self.logger:
            self.logger.log(level, msg, *args, exc_info=exception)

    @property
    def vault(self):
        return self.inner_vault

    def _create_vault_file(self):
        """Creates a database file if one has been defined for this vault"""
        if not self.vault_filename_to:
            return

        dirs_path = os.path.dirname(self.vault_filename_to)
        os.makedirs(dirs_path, exist_ok=True)

        file = open(self.vault_filename_to, "w")
        file.write(json.dumps(dict(), indent=2))
        file.write("\n")
        file.close()
        return file

    def vaulter(self,
                *flags: VaultFlags,
                input_keys: Union[Key, list, tuple] = None,
                return_keys: Union[Key, list, tuple] = None,
                ) -> Callable:
        """
        Decorator to define a function as a vaulted function.
        A vaulted function works a lot different to a normal function.
        A vault works like a key-value storage. A vaulted function will get its arguments
        by accessing them from the vault, and then store any return value back in the vault.

        :param input_keys: Can be of type: Key, list, tuple. Default: None. Keys must be defined in the
         keyring for this specific vault.
        :param return_keys: Can be of type: str, list, tuple. Default: None. Keys must be defined in the
         keyring for this specific vault.
        :param flags: Optional argument for defining some flags for this vaulted function. Flags that have an effect:
         VaultFlags.debug(),
         VaultFlags.input_var_can_be_missing(),
         VaultFlags.permit_modifications()
        """
        input_keys = input_keys if input_keys else list()
        return_keys = return_keys if return_keys else list()

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
                input_kwargs = self._vaulter__build_input_var_keys(input_keys, kwargs, *flags)
                kwargs.update(input_kwargs)
                all_flags = self._get_all_flags(*flags)
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

                self.log(f"======= Calling {func.__module__}.{func.__name__} ========")
                return input_kwargs

            def post_call(ret):
                self._vaulter__handle_return_vars(ret, return_keys, *flags)
                self.log(f"<<<<< {func.__module__}.{func.__name__}:")
                self.log(f"======{'=' * len(func.__module__ + '.' + func.__name__)}=\n")
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
                        self.log(f"Failed to run {func.__module__}.{func.__name__}: {e}", level=logging.ERROR)
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
                        self.log(f"Failed to run {func.__module__}.{func.__name__}: {e}", level=logging.ERROR)
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
        assert len(input_keys) == len(mini)
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
        if VaultFlags.flag_is_set(VaultFlags.clean_return_var_keys(), *all_flags):
            self._clean_return_var_keys(return_keys)
        else:
            mini = self._to_minivault(return_keys, ret, *flags)

            async def validate_keys_in_mini_vault(key):
                assert key in mini, f"Key {key} isn't present in MiniVault; keys in mini: {mini.keys()}"
            concurrent_execution(validate_keys_in_mini_vault, return_keys)

            async def validate_keys_in_return_keys(key):
                assert key in return_keys, f"Key {key} isn't defined as a return-key; return keys: {return_keys}"
            concurrent_execution(validate_keys_in_return_keys, mini.keys())

            self._insert_returnvault(mini, *flags)

    def _clean_return_var_keys(self, return_keys: Union[List[Key], Tuple[Key]]):
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
            # It's not a return vault; Let's turn it into one.
            if isinstance(ret, tuple):
                # It's a tuple, which means it's either meant as a single item, or there are multiple return objects
                if len(return_keys) == 1:
                    assert return_keys[0].valid_type == tuple or VaultFlags.flag_is_set(VaultFlags.return_tuple_is_single_item(), *all_flags), \
                        f"You have defined only a single return key, yet you are returning multiple items, yet the valid type for key {return_keys[0]} is not {tuple}, " \
                        f"nor is {VaultFlags.return_tuple_is_single_item()} set."

                    mini = MiniVault.build(return_keys, [ret])
                else:
                    assert len(return_keys) == len(ret), "The number of return variables and the number of return keys must be identical in order to map the keys to the return variables"
                    mini = MiniVault.build(return_keys, ret)
            else:
                # ret is a single item
                assert len(return_keys) == 1, "There appear to be more than 1 return-key defined, but only a single item that is returned"
                mini = MiniVault.build(return_keys, [ret])
        return mini

    def insert(self, key: Key, value: object, *flags: VaultFlags):
        f"""
        Inserts a value into the vault
        
        :param key: The {key} to insert the value to. Type must be {Key} 
        :param value: The object to assign to {key}
        :param flags: An optional set of flags to tweak the behavior of the insert. Flags that have an effect: 
         VaultFlags.permit_modifications(), 
         VaultFlags.debug()
        """
        # Assert that key has correct type
        self._assert_key_is_correct_type(key)

        self._insert__assert_key_in_keyring(key)

        self._configure_log_levels_based_on_flags(*self._get_all_flags(*flags))

        # Key must be as an iterable, but value doesn't have to be
        mini = self._to_minivault([key], value, *flags)
        self._insert_returnvault(mini, *flags)
        self._reset_log_levels()

    def _insert_returnvault(self, mini: MiniVault, *flags):
        with self.lock:
            all_flags = self._get_all_flags(*flags)

            if VaultFlags.flag_is_set(VaultFlags.return_values_cannot_be_none(), *all_flags):
                assert all([v for v in mini.values() if v is not None]), f"Some or all values returned are {None}, and {VaultFlags.return_values_cannot_be_none()} " \
                                                                         f"has been defined which means no return value may be {None}"

            if not VaultFlags.flag_is_set(VaultFlags.permit_modifications(), *all_flags):
                keys_already_in_vault = [k for k in mini.keys() if k in self]
                assert len(keys_already_in_vault) == 0, f"Keys {keys_already_in_vault} are already in the vault and {VaultFlags.permit_modifications()} is not set. " \
                                                        f"By default, modifications to existing keys are not permitted."
            self.log("-------------------")
            self.log("Variables going in:")
            for ret_key, ret_value in mini.items():
                self.log(f"{ret_key}: ({type(ret_value)}) -- {ret_value}")
            self.vault.put(mini)
            self.log("-----------------")

    def _insert__assert_key_in_keyring(self, key: Key, skip=False):
        """Assert that the key is in the keyring. This step is skipped if force==True"""
        if skip:
            # Skip this step
            return
        assert key in self.keys

    def _insert__assert_value_may_be_inserted(self, key: Key, value: object, modifications_permitted=False):
        # Validate that key doesn't already exist in the vault, or that modifications_permitted==True
        assert key not in self or modifications_permitted, f"Key {key} already exists in the vault and modifications to existing variables are not permitted."

        # Validate the type of the value to insert into the vault
        assert key.type_is_valid(value), f"Value of type {type(value)} is not permitted; Valid type: {key.valid_type}"

    def get_multiple(self, keys: List[Key], *flags: VaultFlags) -> MiniVault:
        f"""
        Get multiple objects from the vault that are mapped to keys in {keys}. 
        
        :param keys: A list of keys to get the objects for. Must be a list of {Key} objects
        :param flags: An optional set of flags to tweak the behavior of the get. Flags that have an effect:
         VaultFlags.debug(),
         VaultFlags.input_var_can_be_missing()
        :param default: An optional argument to define which value to return as default is the value doesn't exist in the vault. Default is {None}
        :return: A ReturnVault with all the objects in the vault mapped to the keys, or {None} if it's not in the vault.  
        """
        all_flags = self._get_all_flags(*flags)
        mini = MiniVault()
        for key in keys:
            self._assert_key_is_correct_type(key)
        with self.lock:
            self._try_reload_from_file()

            self._configure_log_levels_based_on_flags(*all_flags)
            if not VaultFlags.flag_is_set(VaultFlags.input_var_can_be_missing(), *all_flags):
                for key in keys:
                    assert key in self, f"Key {key} is not mapped to an object in the vault; it appears to be missing in the vault. " \
                                        f"You can set the flag '{VaultFlags.input_var_can_be_missing()}' to avoid this, in which case the value will be {None}, or make sure a value is mapped to it."
            [mini.update({key: self.vault.get(key)}) for key in keys]
            self._reset_log_levels()
        return mini

    def get(self, key: Key, *flags: VaultFlags, default=None):
        f"""
        Get an object from the vault that is mapped to {key}. 
        
        :param key: The key to get an object for. Must be of type {Key}
        :param flags: An optional set of flags to tweak the behavior of the get. Flags that have an effect:
         VaultFlags.debug(),
         VaultFlags.input_var_can_be_missing()
        :param default: An optional argument to define which value to return as default is the value doesn't exist in the vault. Default is {None}
        :return: The object in the vault mapped to the key, or {None} if it's not in the vault.  
        """
        all_flags = self._get_all_flags(*flags)
        # Assert that key has correct type
        self._assert_key_is_correct_type(key)

        with self.lock:
            self._try_reload_from_file()

            self._configure_log_levels_based_on_flags(*all_flags)

            if not VaultFlags.flag_is_set(VaultFlags.input_var_can_be_missing(), *all_flags):
                assert key in self, f"Key {key} is not mapped to an object in the vault; it appears to be missing in the vault. " \
                                    f"You can set the flag '{VaultFlags.input_var_can_be_missing()}' to avoid this, in which case the value will be {None}, or make sure a value is mapped to it."

            self.log(f"Getting value for key {key} from vault")
            value = self.vault.get(key, default)

            self._reset_log_levels()
            return value

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
        if self.vault_filename_from and self.live_update:
            current_hash = self._get_vault_file_hash()

            # If current hash is an empty string, that means no hash was able to be acquired. In this case, there is no file to load from; Raise FileNotFoundError
            if current_hash == "":
                raise FileNotFoundError(f"Failed to read from file {self.vault_filename_from} to get the current "
                                        f"contents of it to perform live updates. This means you've created a vault "
                                        f"from a file that doesn't exist and set it to perform live updates, but you "
                                        f"tried to read from the vault-file before the vault-file was created. This "
                                        f"is simply not permitted and you will have to look at your workflow to "
                                        f"figure out an appropriate solution for this problem. ")

            if current_hash != self.vault_file_from_hash:
                mini = create_return_vault_from_file(self.vault_filename_from, self.keyring_class)
                self.vault_file_from_hash = current_hash
                self.vault.put(mini)

    def _get_vault_file_hash(self):
        if not self.vault_filename_from:
            return ""
        else:
            try:
                return md5hash(self.vault_filename_from)
            except FileNotFoundError as e:
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
        if VaultFlags.flag_is_set(VaultFlags.silent(), *all_flags) and VaultFlags.flag_is_set(VaultFlags.debug(), *all_flags):
            # Don't modify any logging levels; debug and silent cancel each other out
            pass
        elif VaultFlags.flag_is_set(VaultFlags.silent(), *all_flags):
            configure_logger(self.logger, overall_level=logging.INFO)
        elif VaultFlags.flag_is_set(VaultFlags.debug(), *all_flags):
            configure_logger(self.logger, stream_level=logging.DEBUG)

    def _reset_log_levels(self):
        configure_logger(self.logger, overall_level=logging.DEBUG, stream_level=logging.INFO, file_level=logging.DEBUG)
