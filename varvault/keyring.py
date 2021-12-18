from __future__ import annotations

import re
import functools
import inspect
import warnings

from typing import *


def validator(function_asserts: bool = None, function_returns_bool: bool = None, skip_source_assertions: bool = False) -> Callable:
    f"""
    Decorator that is used to register a function as a validator-function used for varvault-keys.
    A validator-function assigned to a key will be executed based on how it's registered.
    
    If no argument is passed to the function, {function_asserts} will be set to {True}.

    :param function_asserts: Used to tell varvault that the function will do the validation by performing an assert
    :param function_returns_bool: Used to tell varvault that the function will return a boolean that varvault will assert to be True.
    :param skip_source_assertions: Used to tell this decorator to skip source-assertions that verify that assert or return is done in the  .  
    """
    assert isinstance(function_asserts, bool) or function_asserts is None, f"'function_asserts' must be a bool, or {None}"
    assert isinstance(function_returns_bool, bool) or function_returns_bool is None, f"'function_returns_bool' must be a bool, or {None}"
    if function_asserts and function_returns_bool:
        raise SyntaxError("You've set both 'function_asserts' and 'function_returns_bool' to True; 'function_asserts' takes precedence. Is this what you really want?")
    if not function_asserts and not function_returns_bool:
        function_asserts = True

    def wrap_outer(func: Callable) -> Callable:

        assert callable(func), f"Object {func} is not a callable"
        argspecs = inspect.getfullargspec(func)

        assert len(argspecs.args) == 1, f"You've defined more arguments (or no arguments) for the validator function than you are allowed to. There must be exactly one argument defined in the signature."

        source = inspect.getsource(func)
        if function_asserts:
            assert re.findall(re.compile(r".*assert .*"), source) or skip_source_assertions, "No assert-statement found in the functions source. That doesn't seem right if you are planning to do an assert in the function."
        elif function_returns_bool:
            if argspecs.annotations.get("return") != bool:
                warnings.warn("If you define the validator-function to say that it returns a bool, you should really also annotate the function to say it returns a bool.", SyntaxWarning)
            assert re.findall(re.compile(r".*return .*"), source) or skip_source_assertions, "No return-statement found in the functions source. That doesn't seem right if you are planning to return a bool that varvault is meant to assert."

        @functools.wraps(func)
        def wrap_inner(keyvalue: object):
            assert callable(func)
            if function_asserts:
                func(keyvalue)
            elif function_returns_bool:
                ret = func(keyvalue)
                assert isinstance(ret, bool), f"The return value is of type {type(ret)}, not of type {bool}, " \
                                              f"and you have said that the function will return a bool through 'function_returns_bool' being set to {True}"
                assert ret is True, f"The validator-function {func.__name__} returned False for key-value: {keyvalue}"
        return wrap_inner
    return wrap_outer


class Key(str):
    def __new__(cls, key_name, valid_type: Type = None, can_be_none: bool = False, validators: Union[List[Callable], Tuple[Callable, ...], Callable] = None):
        f"""
        Creates a key that is based on a str-object. 
        
        :param key_name: The name of the key. Note that the name must be compatible as a variable name in Python, meaning no special characters are allowed.        
        :param valid_type: The type to validate the value of the object mapped to this key. E.g., if {valid_type} is {str}, then you cannot map an {int} to the key.
         If {None}, no validation will be done.
        :param can_be_none: Used to tell varvault that this key may be mapped to a value that is set to {None}.
        :param validators: A tuple or list of validator functions to run when writing a value to the key. Functions used for this must be decorated using {validator}.
        """
        obj = super().__new__(cls, key_name)
        obj.key_name = key_name
        obj.can_be_none = can_be_none
        obj.valid_type = valid_type
        obj.validators = cls._convert_validators_to_tuple(validators)
        return obj

    def __eq__(self, other: Key or str):
        if not isinstance(other, (Key, str)):
            return False

        if isinstance(other, Key):
            return self.key_name == other.key_name
        else:
            return self.key_name == other

    def __hash__(self):
        return hash(self.key_name)

    @classmethod
    def _convert_validators_to_tuple(cls, validators):
        assert validators is None or callable(validators) or isinstance(validators, (list, tuple))
        if isinstance(validators, (list, tuple)):
            for validator_function in validators:
                assert callable(validator_function)
        if validators is None:
            return tuple()
        if callable(validators):
            return tuple([validators])
        return tuple(validators)

    def type_is_valid(self, obj):
        def run_validators():
            for validator_function in self.validators:
                validator_function(obj)

        if not self.valid_type:
            # No valid types defined. Return True if validators pass
            run_validators()
            return True
        else:
            if self.can_be_none:
                if obj is None:
                    return True
                if isinstance(obj, self.valid_type):
                    run_validators()
                    return True
                try:
                    if issubclass(obj, self.valid_type):
                        return True
                except:
                    pass
                return False
            else:
                if isinstance(obj, self.valid_type):
                    run_validators()
                    return True
                try:
                    if issubclass(obj, self.valid_type):
                        return True
                except:
                    pass
                return False


class Keyring(object):
    """Base class for keys to be used for a vault. A class which extends
    this class must be used for defining your own keyring."""

    @classmethod
    def get_keys_in_keyring(cls) -> Dict[str, Key]:
        """Returns all keys in the keyring as a dict on this format: Dict[str: Key]"""
        keys = dict()
        for key, value in cls.__dict__.items():
            if not isinstance(value, Key):
                continue
            assert key == value, f"The name of a key in a keyring must match the variable's name; varname: {key}, value: {value}"
            keys[key] = value
        return keys

    @classmethod
    def get_key_by_matching_string(cls, key_str: str) -> Key:
        """Returns a key in the keyring that matches the string passed to the function"""
        try:
            return cls.__dict__[key_str]
        except KeyError:
            raise KeyError(f"Failed to get matching key for string: {key_str}. "
                           f"It doesn't appear to exist in the keyring: {cls.get_keys_in_keyring().values()}")
