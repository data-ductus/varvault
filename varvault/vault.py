from __future__ import annotations

import json
import asyncio
import inspect
import logging
import time
import warnings
import functools
import traceback

from typing import *
from threading import Lock

from .resource import BaseResource
from .keyring import Keyring, Key
from .logger import get_logger, configure_logger
from .minivault import MiniVault
from .subscriber_thread import SubscriberThread
from .utils import concurrent_execution, AssignedByVault, assert_and_raise
from .flags import Flags


class VarVault(dict):

    def __setitem__(self, key, value):
        data = {key: value}
        if self.resource and self.resource.writable(data):
            self.writable_args.update(data)

        super(VarVault, self).__setitem__(key, value)

    def __delitem__(self, key):
        if self.resource and key in self.writable_args:
            del self.writable_args[key]

        super(VarVault, self).__delitem__(key)

    @functools.singledispatchmethod
    def _put(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    @_put.register
    def _mv(self, mini: MiniVault):
        f"""{self._put} to add a MiniVault"""

        async def _put(item):
            key, value = item
            self.__setitem__(key, value)
        concurrent_execution(_put, mini.items())
        self.write()

    @_put.register
    def _k_v(self, key: Key, value: object):
        f"""{self._put} to add a key-value pair"""
        self.__setitem__(key, value)
        self.write()

    def write(self):
        # No resource has been defined, which means we cannot write anything to the file
        if not self.resource:
            return

        # Write is not permitted
        if not self.resource.mode_properties.write:
            # If it's initialized and live-update isn't permitted, then we should raise a warning because we are clearly trying to write to a file that we cannot write to
            if self.initialized and not self.resource.mode_properties.live_update:
                warnings.warn("It appears you are trying to write to a resource that is not permitted to write to and the vault has already been initialized. "
                              "This is not permitted and you should consider removing the action that triggered this.")
            return

        # Try to write writable_args to vault_file if it has been defined
        self.resource.write(self.writable_args)

    def __init__(self,
                 *flags: Flags,
                 keyring: Type[Keyring] = None,
                 name: str = None,
                 resource: BaseResource = None,
                 logger: logging.Logger = None,
                 initial_vars: MiniVault = None,
                 **extra_keys):
        f"""
        Creates a vault-object. You should ideally create a vault from the existing factory functions. 
        
        :param flags: A set of flags used to tweak the behavior of the vault object. See {Flags} for what flags can be used and what they do.
        :param keyring: The {Keyring} class used for this vault.  
        :param name: Optional. The name of the vault. This is used when creating a logfile for logging information to, unless a {logger} is passed.  
        :param resource: The resource to for the vault.  
        :param logger: Optional. A specific logger to log to in-case you do not want to use the built-in logger in varvault.
        :param initial_vars: Optional. A {MiniVault} containing variables to be added to the vault when it is created. 
         The factory function 'create' will provide this if the mode for a resource is allowed to do 'load'. 
        :param extra_keys: Optional. A kwargs-object with extra keys that are not defined in the {keyring}. This can be useful when you have a lot of keys that you might 
         want to handle in a programmatic sense rather than in a pre-defined sense. 
        """
        super().__init__()

        assert_and_raise(keyring is not None and issubclass(keyring, Keyring),
                         ValueError(f"{self.__init__.__name__} requires a {Keyring} class to be passed as the {keyring} argument"))

        assert_and_raise(name is None or isinstance(name, str),
                         ValueError(f"'name' must be of type {str}, or {None}, not ({type(name)})"))

        assert_and_raise(resource is None or isinstance(resource, BaseResource),
                         ValueError(f"'resource' must be of type {BaseResource}, or {None}, not {type(resource)}"))

        assert_and_raise(logger is None or isinstance(logger, logging.Logger),
                         ValueError(f"'logger' must be of type {logging.Logger}, or {None}, not {type(logger)}"))

        assert_and_raise(not Flags.is_set(Flags.clean_output_keys, *flags),
                         ValueError(f"You really should not set the flag {Flags.clean_output_keys} to the vault itself as that would be an extremely bad idea."))

        for key_name, key in extra_keys.items():
            assert_and_raise(isinstance(key_name, str) and isinstance(key, Key),
                             ValueError(f"extra_keys is not setup correctly; The pattern {{{key_name} ({type(key_name)}): {key} ({type(key)})}} is incorrect. Correct pattern would be {{{key_name} ({str}): {key} ({Key})}}"))

        disable_logger = Flags.is_set(Flags.disable_logger, *flags)
        remove_existing_log_file = Flags.is_set(Flags.remove_existing_log_file, *flags)
        if logger:
            self.logger = logger
        else:
            self.logger = get_logger(name, remove_existing_log_file) if not disable_logger else None
        self.writable_args = dict()
        self.initialized = False
        self.times_taken = dict()
        self.keyring_class = keyring
        self.flags: set = set(flags)
        self.resource: BaseResource = resource
        self.functions_as_automatics: Dict[Key, List[Callable]] = dict()
        self.keys_used_by_automatics: Dict[Callable, List[Key]] = dict()
        self.automatic_conditionals: Dict[Callable, Callable] = dict()
        self.running_tasks: Set[SubscriberThread] = set()
        self.threaded_automatics = set()

        if initial_vars and isinstance(initial_vars, MiniVault):
            self._put(initial_vars)
        self.initialized = True

        if self.resource and not self.resource.resource:
            self.resource.create()

        self.lock = Lock()

        # Get the keys from the keyring and expand it with extra keys
        self.keys: Dict[str, Key] = self.keyring_class.get_keys()
        self.keys.update(extra_keys)

        if self.resource:
            self.log(f"Vault writing data to '{self.resource.path}'", level=logging.DEBUG, all_flags=flags)
            if self.resource.mode_properties.live_update:
                self.log(f"Vault doing live updates from '{self.resource.path}' whenever the vault is accessed.", level=logging.DEBUG, all_flags=flags)

    def __contains__(self, key: Key):
        self._assert_key_is_correct_type(key, msg=f"{self.__contains__.__name__} may only be used with a {Key}-object, not {type(key)}")

        if key.key_name not in self.keys:
            warnings.warn(f"{key.key_name} is not defined in the keyring. This is not a problem, but trying to check if the "
                          f"vault contains this key will never succeed; Consider removing the call that triggered this warning.")
            return False

        return super().__contains__(key)

    def __str__(self):

        return super().__str__()

    def as_json_str(self):
        """
        Returns the vault as a json-string, if possible. If not, return as a string.
        :return: A json-string containing the vault.
        """
        try:
            return json.dumps(self, indent=2)
        except json.JSONDecodeError:
            # Probably some objects in the vault that cannot be serialized. Just return the string representation of the vault then.
            return self.__str__()

    def log(self, msg: object, *args, level: int = logging.DEBUG, exception: BaseException = None, all_flags: Union[Set[Flags], Tuple[Flags]] = None):
        if self.logger:
            all_flags = all_flags or self.flags
            assert isinstance(level, int), "Log level must be defined as an integer"
            self._configure_log_levels_based_on_flags(*all_flags)
            self.logger.log(level, msg, *args, exc_info=exception)
            self._reset_log_levels()

    def _configure_log_levels_based_on_flags(self, *all_flags):
        if not self.logger or not Flags.is_set((Flags.silent, Flags.debug), *all_flags):
            # No logger has been assigned for this vault, or no flags that affect the log level has been set. Just return then.
            return
        elif Flags.is_set(Flags.silent, *all_flags) and Flags.is_set(Flags.debug, *all_flags):
            # Use default logging levels; debug and silent cancel each other out
            configure_logger(self.logger)
        elif Flags.is_set(Flags.silent, *all_flags):
            configure_logger(self.logger, overall_level=logging.INFO)
        elif Flags.is_set(Flags.debug, *all_flags):
            configure_logger(self.logger, stream_level=logging.DEBUG, overall_level=logging.DEBUG, file_level=logging.DEBUG)

    def _reset_log_levels(self):
        if not self.logger:
            # No logger has been assigned for this vault. Just return then.
            return
        configure_logger(self.logger, overall_level=logging.DEBUG, stream_level=logging.INFO, file_level=logging.DEBUG)

    # ============================================================
    # manual
    # ============================================================
    def manual(self,
               *flags: Flags,
               input: Union[Key, List[Key], Tuple[Key, ...]] = None,
               output: Union[Key, List[Key], Tuple[Key, ...]] = None) -> Callable:
        f"""
        Decorator to register a function as a vaulted function that must be called MANUALLY.
        A vaulted function works a lot different to a normal function.
        A vault works like a key-value storage. A vaulted function will get its arguments
        by accessing them from the vault, and then store any returned value back in the vault.

        :param input: Can be of type: {Key}, {list}, {tuple}. Default: {None}. Keys must be defined in the
         keyring for this specific vault.
        :param output: Can be of type: {Key}, {list}, {tuple}. Default: {None}. Keys must be defined in the
         keyring for this specific vault.
        :param flags: Optional argument for defining some flags for this vaulted function. Flags that have an effect:
         {Flags.debug},
         {Flags.silent},
         {Flags.input_key_can_be_missing},
         {Flags.permit_modifications},
         {Flags.split_output_keys},
         {Flags.output_key_can_be_missing},
         {Flags.clean_output_keys},
         {Flags.no_error_logging},
         {Flags.use_signature_for_input_keys},
         {Flags.output_key_replaces_input_key},
        """
        all_flags = self._get_all_flags(*flags)

        # Convert input- and output keys to a list if it's a single key to make it easier to handle
        input, output = self._convert_input_keys_and_output_keys(input, output)

        # Assert that the keys are in the keyring
        self._assert_keys_in_keyring(input)
        self._assert_keys_in_keyring(output)

        def wrap_outer(func):
            [key.usages.add_input(func) for key in input]
            [key.usages.add_return(func) for key in output]
            if Flags.is_set(Flags.use_signature_for_input_keys, *all_flags):
                self._manual__populate_input_keys_from_signature(func, input)

            # Separate handling if the decorated function uses the coroutine API
            if asyncio.iscoroutinefunction(func):
                return self._inner_async(func, *all_flags, input=input, output=output)
            else:
                return self._inner_standard(func, *all_flags, input=input, output=output)
        return wrap_outer

    def _manual__populate_input_keys_from_signature(self, func, input_keys):
        signature = inspect.signature(func)
        faulty_params = list()
        keys = self.keyring_class.get_keys()
        for parameter in signature.parameters.values():
            valid_kind = parameter.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD or parameter.kind == inspect.Parameter.KEYWORD_ONLY

            param_name = parameter.name
            correct_default = parameter.default == AssignedByVault
            if param_name in keys and valid_kind and param_name not in input_keys:
                if not correct_default:
                    faulty_params.append((param_name, "The default value must be assigned to 'varvault.AssignedByVault'"))
                else:
                    input_keys.append(self.keyring_class.get_key_by_matching_string(parameter.name))
            elif correct_default and param_name not in keys:
                faulty_params.append((param_name, "You assigned the parameter a correct default value, but the parameter doesn't exist as a key in the keyring. "
                                                  "Did you make a typo in the parameter name? We'll be failing this for you because you more than likely made a mistake"))
        if faulty_params:
            raise AssertionError(f"Errors found in the signature: {faulty_params}")

    def _manual__build_input_keys(self, input_keys, *all_flags, **kwargs):
        mini = self.get(input_keys, *all_flags)
        if Flags.is_set(Flags.input_key_can_be_missing, *all_flags):
            [mini.add(key, None) for key in input_keys if key not in mini]

        assert len(input_keys) == len(mini), \
            f"The number of items acquired from {self.get.__name__} is not the same as the number of input-keys to the method, " \
            f"which it should be. This is probably a bug."

        for key in mini.keys():
            assert key not in kwargs, f"Key {key} seems to already exist in kwargs used for the function decorated with '@{self.manual.__name__}'"

        return mini

    # ============================================================
    # automatic
    # ============================================================
    def automatic(self, *flags: Flags, input: Union[Key, List, Tuple] = None, output: Union[Key, List, Tuple] = None, condition: Callable = lambda: True, threaded: bool = False):
        f"""
        Registers a function as a subscriber to the vault. The function will be called AUTOMATICALLY whenever all of the given input_keys is inserted into the vault.
        
        Note that since this function runs within the context of varvault, there is no way to insert other arguments to the subscribed function, 
        or to capture any of the return variables. If you need to do that, you can use the {self.manual} decorator instead.
        
        It's entirely possible to chain multiple automatic functions together that each depend on each other. They will run as soon as all of their input keys are configured in the vault. 
        
        :param input: Can be of type: {Key}, {list}, {tuple}. Default: {None}. Keys must be defined in the
         keyring for this specific vault.
        :param output: Can be of type: {Key}, {list}, {tuple}. Default: {None}. Keys must be defined in the
         keyring for this specific vault.
        :param condition: A function, like a lambda, that returns a boolean. If the function returns {False}, the subscriber will not be called even if the required keys exist in the vault.
        :param threaded: If set to {True}, the subscriber will be called in a separate thread. This is useful if the function doesn't need to be monitored and takes long to run.
        :param flags: Optional argument for defining some flags for this vaulted function. Flags that have an effect:
         {Flags.debug},
         {Flags.silent},
         {Flags.input_key_can_be_missing},
         {Flags.permit_modifications},
         {Flags.split_output_keys},
         {Flags.output_key_can_be_missing},
         {Flags.clean_output_keys},
         {Flags.no_error_logging},
         {Flags.use_signature_for_input_keys},
         {Flags.output_key_replaces_input_key},
        """
        input, output = self._convert_input_keys_and_output_keys(input, output)

        assert_and_raise(all(isinstance(key, Key) for key in input),
                         TypeError(f"input_keys must be of type {Key}, {List} or {Tuple}"))

        assert_and_raise(not any(key in output for key in input),
                         KeyError(f"input and output cannot contain the same keys. This would effectively mean that the function subscribes "
                                  f"to itself and would run forever if {Flags.permit_modifications.name} is set, or crash if it's not set."))

        all_flags = self._get_all_flags(*flags)

        def wrap_outer(func):

            [key.usages.add_input(func) for key in input]
            [key.usages.add_return(func) for key in output]
            # Separate handling if the decorated function uses the coroutine API
            if asyncio.iscoroutinefunction(func):
                raise ValueError(f"Async subscriber functions do not work because async functions cannot truly run in the background. Use {self.automatic.__name__} with 'threaded={True}' instead.")

            else:
                f = self._inner_standard(func, *all_flags, input=input, output=output)
            if threaded:
                self.threaded_automatics.add(f)
            self.keys_used_by_automatics[f] = list()
            self.automatic_conditionals[f] = condition
            for key in input:
                if key not in self.functions_as_automatics:
                    self.functions_as_automatics[key] = list()
                self.functions_as_automatics[key].append(f)
                self.keys_used_by_automatics[f].append(key)
            self._dispatch_subscriber(f, input, threaded)
            return f

        return wrap_outer

    def purge_stopped_thread(self, subscriber_thread: SubscriberThread):
        if subscriber_thread in self.running_tasks:
            self.logger.debug(f"Removing stopped thread for {subscriber_thread.subscriber.__name__} from the running tasks")
            self.running_tasks.remove(subscriber_thread)

    # ============================================================
    # insert
    # ============================================================
    def insert(self, key: Key, value: object, *flags: Flags):
        f"""
        Inserts a {value} into the vault mapped to {key}.
        
        :param key: The {key} to insert the value to. Type must be {Key} 
        :param value: The object to assign to {key}
        :param flags: An optional set of flags to tweak the behavior of the insert. Flags that have an effect: 
         {Flags.permit_modifications},
         {Flags.return_values_cannot_be_none}, 
         {Flags.debug},
         {Flags.silent}
        """
        # Key must be as an iterable, but value doesn't have to be
        mini = self._to_minivault([key], value, *self._get_all_flags(*flags))
        self.insert_minivault(mini, *self._get_all_flags(*flags))

    # ============================================================
    # insert_minivault
    # ============================================================
    def insert_minivault(self, mini: MiniVault, *flags):
        f"""
        Inserts a {MiniVault} into the vault.
        
        :param mini: The {MiniVault} to insert into the vault. 
        :param flags: An optional set of flags to tweak the behavior of the insert. Flags that have an effect: 
         {Flags.permit_modifications},
         {Flags.return_values_cannot_be_none}, 
         {Flags.debug},
         {Flags.silent}
        """
        all_flags = self._get_all_flags(*flags)

        # Assert that key has correct type
        self._assert_keys_in_keyring(mini.keys())

        async def run_modifiers(item: Tuple[Key, object]):
            key, value = item
            mini[key] = key.run_modifiers(value)

        concurrent_execution(run_modifiers, mini.items())

        async def assert_key_and_value_may_be_inserted(item: Tuple[Key, object]):
            key, value = item
            if Flags.is_set(Flags.return_values_cannot_be_none, *all_flags):
                assert_and_raise(value is not None, ValueError(f"The value mapped to {key} is {None} and {Flags.return_values_cannot_be_none} is defined."))

            self._insert__assert_value_may_be_inserted(key, value, modifications_permitted=Flags.is_set(Flags.permit_modifications, *all_flags))
        concurrent_execution(assert_key_and_value_may_be_inserted, mini.items())

        with self.lock:
            self.log("-------------------", all_flags=all_flags)
            self.log("Variables going in:", all_flags=all_flags)
            for ret_key, ret_value in mini.items():
                self.log(f"<-- {ret_key}: ({type(ret_value)}) -- {ret_value}", all_flags=all_flags)
            self._put(mini)

            self.log("-----------------", all_flags=all_flags)
        self._dispatch_subscribers(mini.keys())

    def _insert__assert_value_may_be_inserted(self, key: Key, value: object, modifications_permitted=False):
        # Validate that key doesn't already exist in the vault, or that modifications_permitted==True
        assert_and_raise(key not in self or modifications_permitted, KeyError(f"Key {key} already exists in the vault and modifications to existing variables are not permitted."))

        # Validate the type of the value to insert into the vault
        assert_and_raise(key.type_is_valid(value), ValueError(f"Key '{key}' requires type to be '{key.valid_type}', but type for value is '{type(value)}'."))

    # ============================================================
    # get
    # ============================================================
    @overload
    def get(self, key: Key, *flags: Flags, default=None) -> Any:
        f"""
        Get an object from the vault that is mapped to {key}. 
        
        :param key: The key to get an object for. Must be of type {Key}
        :param flags: An optional set of flags to tweak the behavior of the get. Flags that have an effect:
         {Flags.debug},
         {Flags.silent},
         {Flags.input_key_can_be_missing}
        :param default: An optional argument to define which value to return as default is the value doesn't exist in the vault. Default is {None}. Only applicable if {Flags.input_key_can_be_missing} is set.
        :return: The object in the vault mapped to the {key}, or {None} if it's not in the vault.  
        """
        ...

    @overload
    def get(self, keys: list or tuple, *flags: Flags) -> MiniVault:
        f"""
        Get multiple objects from the vault that are mapped to keys in {keys}. 
        
        :param keys: A list of keys to get the objects for. Must be a list of {Key} objects
        :param flags: An optional set of flags to tweak the behavior of the get. Flags that have an effect:
         {Flags.debug},
         {Flags.silent},
         {Flags.input_key_can_be_missing}
        :return: A {MiniVault} with all the objects in the vault mapped to the keys, or {None} if it's not in the vault.  
        """
        ...

    def get(self, *args, **kwargs):
        def multiple(keys, *flags):
            all_flags = self._get_all_flags(*flags)
            mini = MiniVault()
            self._assert_keys_in_keyring(keys)
            with self.lock:
                self._try_reload_from_file(*all_flags)

                if not Flags.is_set(Flags.input_key_can_be_missing, *all_flags):
                    for key in keys:
                        assert_and_raise(key in self, KeyError(f"Key {key} is not mapped to an object in the vault; it appears to be missing in the vault. "
                                                               f"You can set the flag '{Flags.input_key_can_be_missing}' to avoid this, "
                                                               f"in which case the value will be {None}, or make sure a value is mapped to it. "
                                                               f"Known functions/methods where this key is used as an output key: {key.usages.as_return}"))
                [mini.update({key: self[key]}) for key in keys if key in self]
            return mini

        def single(key, *flags, default=None):
            mv = multiple([key], *flags)
            if Flags.is_set(Flags.input_key_can_be_missing, *flags):
                return mv.get(key, default)
            return mv.get(key)

        keys, *flags = args
        if isinstance(keys, (list, tuple)):
            return multiple(keys, *flags)
        elif isinstance(keys, Key):
            return single(keys, *flags, default=kwargs.get("default"))
        else:
            raise NotImplementedError(f"Type {type(keys)} is not supported for the 'get' method. Supported types are: {Key}, {list} and {tuple}.")

    # ============================================================
    # lambdavaulter
    # ============================================================
    def lambdavaulter(self,
                      lambda_func: Callable,
                      *flags: Flags,
                      input_keys: Union[Key, List[Key, ...], Tuple[Key, ...]] = None,
                      output_keys: Union[Key, List[Key, ...], Tuple[Key, ...]] = None):
        f"""
        Function to wrap a lambda like you would decorate a function. 
        
        Uses the {self.manual} function to wrap the lambda. See {self.manual} function for information about flags that have an effect on this function.
        
        Why you would like to do this, who knows. But you can do it. 
        
        :param lambda_func: The lambda to wrap. 
        :param flags: A set of flags to use when wrapping the lambda. 
        :param input_keys: The keys to use as input for the lambda. 
        :param output_keys: The keys to return from the lambda. 
        :return: A wrapped lambda. 
        """
        return self.manual(*flags, input=input_keys, output=output_keys)(lambda_func)

    def await_running_tasks(self, timeout: float = 0, exception: Exception = None):
        f"""
        Wait for all running tasks to finish.
        
        :param timeout: The timeout in seconds to wait for all tasks to finish. Default is 0, which literally means 0 seconds. If this function is called with {timeout}=0, 
         it means you expect all tasks to be finished by now. If you don't expect all tasks to be finished by now, you should probably set a timeout.
        """
        start = time.time()
        while self.running_tasks:
            if time.time() - start > timeout:
                self.logger.info(f"Timeout of {timeout} seconds reached while waiting for no running tasks. ")
                if exception:
                    raise exception
                raise TimeoutError(f"Timeout of {timeout} seconds reached while waiting for no running tasks.")

    # ============================================================
    # privates
    # ============================================================

    def _convert_input_keys_and_output_keys(self, input: Union[Key, List, Tuple], output: Union[Key, List, Tuple]) -> Tuple[List, List]:
        input = input if input else list()
        output = output if output else list()

        # Validate the input to the decorator
        self._validate_input(input, output)

        if isinstance(input, Key):
            input = [input]
        if isinstance(output, Key):
            output = [output]

        assert_and_raise(isinstance(input, (list, tuple)), TypeError(f"Input keys doesn't have the correct type; actual type: {type(input)}"))
        assert_and_raise(isinstance(output, (list, tuple)), TypeError(f"Output keys doesn't have the correct type; actual type: {type(output)}"))
        return input, output

    def _validate_input(self, input_keys, output_keys):
        assert_and_raise(isinstance(input_keys, (Key, list, tuple)),
                         TypeError(f"input_keys must be of type {Key}, {list}, or {tuple}"))
        assert_and_raise(isinstance(output_keys, (Key, list, tuple)),
                         TypeError(f"output_keys must be of type {Key}, {list}, or {tuple}"))

    def _inner_async(self, func, *all_flags: Flags, input: List[Key] = None, output: List[Key] = None):
        f"""Inner async wrapper for {self.manual}/{self.automatic} decorators"""
        func_module_name = f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        async def wrap_inner_async(*args, **kwargs):
            #
            # Do pre-call related stuff
            #
            input_kwargs = self._pre_call(input, func_module_name, *all_flags, **kwargs)
            try:
                ret = await func(*args, **input_kwargs)
            except Exception as e:
                if not Flags.is_set(Flags.no_error_logging, *all_flags):
                    # Flag to not log error is NOT set, so we should log the error and then raise the error
                    self.log(f"Failed to run {func_module_name}: {e}", level=logging.ERROR, all_flags=all_flags)
                    self.log(str(traceback.format_exc()).rstrip("\n"), level=logging.ERROR, all_flags=all_flags)
                raise

            #
            # Do post-call related stuff
            #
            self._post_call(ret, input, output, func_module_name, *all_flags)

            return ret
        return wrap_inner_async

    def _inner_standard(self, func, *all_flags: Flags, input: List[Key] = None, output: List[Key] = None):
        f"""Inner standard wrapper for {self.manual}/{self.automatic} decorators"""
        func_module_name = f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrap_inner(*args, **kwargs):
            #
            # Do pre-call related stuff
            #
            input_kwargs = self._pre_call(input, func_module_name, *all_flags, **kwargs)

            try:
                ret = func(*args, **input_kwargs)
            except Exception as e:
                if not Flags.is_set(Flags.no_error_logging, *all_flags):
                    # Flag to not log error is NOT set, so we should log the error and then raise the error
                    self.log(f"Failed to run {func_module_name}: {e}", level=logging.ERROR, all_flags=all_flags)
                    self.log(str(traceback.format_exc()).rstrip("\n"), level=logging.ERROR, all_flags=all_flags)
                raise

            #
            # Do post-call related stuff
            #
            self._post_call(ret, input, output, func_module_name, *all_flags)

            return ret
        return wrap_inner

    def _pre_call(self, input: Union[List[Key], Tuple[Key]], func_module_name: str, *all_flags: Flags, **kwargs):
        input_kwargs = self._manual__build_input_keys(input, *all_flags, **kwargs)
        kwargs.update(input_kwargs)

        self.log(f"======{'=' * len(func_module_name)}=", all_flags=all_flags)
        self.log(f">>>>> {func_module_name}:", all_flags=all_flags)
        if input_kwargs:
            self.log(f"-------------", all_flags=all_flags)
            self.log(f"Input kwargs:", all_flags=all_flags)
            for kwarg_key, kwarg_value in input_kwargs.items():
                self.log(f"--> {kwarg_key}: ({type(kwarg_value)}) -- {kwarg_value}", all_flags=all_flags)
            self.log(f"-------------", all_flags=all_flags)
        input_kwargs.update(kwargs)

        self.log(f"======= Calling {func_module_name} ========", all_flags=all_flags)
        return input_kwargs

    def _post_call(self, ret, input_keys, output_keys, func_module_name, *all_flags: Flags):
        self._handle_output_keys(ret, input_keys, output_keys, *all_flags)
        self.log(f"<<<<< {func_module_name}:", all_flags=all_flags)
        self.log(f"======{'=' * len(func_module_name)}=\n", all_flags=all_flags)
        self._reset_log_levels()

    def _handle_output_keys(self, ret, input_keys, output_keys, *all_flags):

        if not output_keys:
            # No output keys were defined; Just return from here then as there is nothing else to do.
            return

        if Flags.is_set(Flags.split_output_keys, *all_flags):
            assert_and_raise(isinstance(ret, MiniVault),
                             ValueError(f"If {Flags.split_output_keys} is defined, you MUST return values in the form of a {MiniVault} object or we cannot determine which keys go where"))
            ret = MiniVault({key: value for key, value in ret.items() if key in output_keys})
        if Flags.is_set(Flags.output_key_can_be_missing, *all_flags):
            assert_and_raise(isinstance(ret, MiniVault),
                             ValueError(f"If {Flags.output_key_can_be_missing} is defined, you MUST return values in the form of a {MiniVault} object or we "
                                        f"cannot determine which keys should be assigned to the vault and which should be skipped."))
        if Flags.is_set(Flags.clean_output_keys, *all_flags):
            self._clean_output_keys(output_keys, *all_flags)
        else:
            mini = self._to_minivault(output_keys, ret, *all_flags)
            if Flags.is_set(Flags.output_key_replaces_input_key, *all_flags):
                assert_and_raise(len(input_keys) == 1 and len(output_keys) == 1, ValueError(f"If {Flags.output_key_replaces_input_key} is defined, you MUST define "
                                                                                            f"exactly one input key and one output key."))
                del self[input_keys[0]]

            async def validate_keys_in_mini_vault(key, can_be_missing=False):
                assert key in mini or can_be_missing, f"Key {key} isn't present in MiniVault; keys in mini: {mini.keys()}. " \
                                                      f"You can set the vault-flag {Flags.output_key_can_be_missing} to skip this validation step"
            concurrent_execution(validate_keys_in_mini_vault, output_keys, can_be_missing=Flags.is_set(Flags.output_key_can_be_missing, *all_flags))

            async def validate_keys_in_output_keys(key):
                assert key in output_keys, f"Key {key} isn't defined as an output-key; output keys: {output_keys}"
            concurrent_execution(validate_keys_in_output_keys, mini.keys())

            self.insert_minivault(mini, *all_flags)

    def _dispatch_subscribers(self, keys: List[Key]):
        potential_functions_to_dispatch = set()
        functions_to_dispatch = set()
        threaded_functions_to_dispatch = set()
        for key in keys:
            functions = self.functions_as_automatics.get(key, [])
            for function in functions:
                potential_functions_to_dispatch.add(function)
        for function in potential_functions_to_dispatch:
            keys_that_must_be_in_vault = self.keys_used_by_automatics.get(function, [])
            may_dispatch = True
            for key in keys_that_must_be_in_vault:
                if key not in self:
                    # Key does not exist in vault. Dispatch is impossible.
                    may_dispatch = False
                    break
            if may_dispatch:
                conditional: Callable = self.automatic_conditionals[function]
                if conditional():
                    if function in self.threaded_automatics:
                        threaded_functions_to_dispatch.add(function)
                    else:
                        functions_to_dispatch.add(function)
        for function in threaded_functions_to_dispatch:
            self._dispatch_subscriber(function, keys, threaded=True)

        for function in functions_to_dispatch:
            self._dispatch_subscriber(function, keys, threaded=False)

    def _dispatch_subscriber(self, function: Callable, keys: List[Key], threaded: bool):
        if not all(key in self for key in keys):
            # May not dispatch; not all keys exist in the vault
            return

        conditional: Callable = self.automatic_conditionals[function]
        if not conditional():
            # May not dispatch; conditional is not met
            return

        if threaded:
            # Dispatch threaded functions.
            thread = SubscriberThread(function, self)
            self.running_tasks.add(thread)
            thread.start()
        else:
            # Dispatch the function.
            function()

    def _get_all_flags(self, *flags):
        self._assert_flag_is_correct_type(*flags)
        all_flags = self.flags.copy()
        all_flags.update(flags)
        return all_flags

    def _assert_flag_is_correct_type(self, *flags: Flags):
        for flag in flags:
            assert_and_raise(isinstance(flag, Flags), TypeError(f"Flag {flag} is not of type {Flags} (type: {type(flag)})"))

    def _assert_key_is_correct_type(self, key: Key, msg=None):
        # Define the error message based on input
        if not msg:
            msg = f"Key {key} is not of required type {Key}"
        assert isinstance(key, Key), msg

    def _assert_keys_in_keyring(self, keys: Union[Tuple[Key], List[Key]]):
        assert isinstance(keys, (list, tuple)), f"Keys {keys} is not of required type {list} or {tuple} (type: {type(keys)})"
        for key in keys:
            self._assert_key_is_correct_type(key)
            assert key in self.keys, f"Key {key} is not in the keyring."

    def _try_reload_from_file(self, *all_flags: Flags):
        """Can be used to reload from a file if changes has been made to it since it was read last time."""
        if self.resource and self.resource.mode_properties.live_update:
            if not self.resource.resource_has_changed():
                return
            self.log(f"Reloading from {self.resource.path}; The content has changed and live-update is enabled.", all_flags=all_flags)
            mv = self.resource.create_mv(**self.keys)
            self._put(mv)

    def _clean_output_keys(self, output_keys: Union[List[Key], Tuple[Key]], *all_flags: Flags):
        self.log(f"Cleaning output keys: {output_keys}", all_flags=all_flags)
        for key in output_keys:
            if not key.valid_type:
                temp = None
                self.log(f"Cleaning key {key} by setting it to None (no valid_type defined for {key})", all_flags=all_flags)
            else:
                try:
                    temp = key.valid_type()
                    self.log(f"Cleaning key {key} by setting it to '{temp}' (key.valid_type = {key.valid_type})", all_flags=all_flags)
                except:
                    temp = None
                    self.log(f"Cleaning key {key} by setting it to '{None}' (valid_type is defined, but no default constructor appears to exist for {key.valid_type})", all_flags=all_flags)
            self._put(key, temp)

    def _to_minivault(self, output_keys, ret, *all_flags) -> MiniVault:
        if isinstance(ret, MiniVault):
            mini = ret
        else:
            # It's not a MiniVault; Let's turn it into one.
            if isinstance(ret, tuple):
                # It's a tuple, which means it's either meant as a single item, or there are multiple return objects
                if len(output_keys) == 1:
                    # There's only one output key defined, which means the keys valid type should be tuple, OR the flag return_tuple_is_single_item is set
                    assert output_keys[0].valid_type == tuple or Flags.is_set(Flags.return_tuple_is_single_item, *all_flags), \
                        f"You have defined only a single output key, yet you are returning multiple items, while the valid type for key " \
                        f"{self.keyring_class.__name__}.{output_keys[0]} is not {tuple}, nor is {Flags.return_tuple_is_single_item} set."

                    mini = MiniVault.build(output_keys, [ret])
                else:
                    assert len(output_keys) == len(ret), "The number of returned variables and the number of output keys must be identical in order to map the keys to the returned variables"
                    mini = MiniVault.build(output_keys, ret)
            else:
                # ret is a single item
                assert len(output_keys) == 1, "There appear to be more than 1 return-key defined, but only a single item that is returned"
                mini = MiniVault.build(output_keys, [ret])
        return mini
