from __future__ import annotations

from typing import *

from .validator import validator


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
        assert validators is None or callable(validators) or isinstance(validators, (list, tuple)), f"Validators {validators} should be {None}, {Callable}, or a {list}/{tuple} of {Callable}"
        if isinstance(validators, (list, tuple)):
            for validator_function in validators:
                assert callable(validator_function), f"Validator must be a {Callable}"
        if validators is None:
            return tuple()
        if callable(validators):
            return tuple([validators])
        return tuple(validators)

    def type_is_valid(self, obj):
        """Checks if the type/value for an object mapped to this key is valid in accordance with the definition of the key."""
        def run_validators():
            f"""Runs the validators. Note that all validators are decorated with the {validator} decorator which is responsible for handling the actual validation."""
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
    this class must be used for defining your own keyring.

    Note that you never have to instantiate this class (i.e. create an object), you just have to create a class that inherits from this class."""

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
