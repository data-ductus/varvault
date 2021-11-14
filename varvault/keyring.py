from __future__ import annotations

from typing import *


class Key(str):
    def __new__(cls, key_name, valid_type: Type = None, can_be_none: bool = False):
        obj = super().__new__(cls, key_name)
        obj.key_name = key_name
        obj.can_be_none = can_be_none
        obj.valid_type = valid_type
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

    def type_is_valid(self, obj):
        if not self.valid_type:
            # No valid types defined. Return True
            return True
        else:
            if self.can_be_none:
                if obj is None:
                    return True
                if isinstance(obj, self.valid_type):
                    return True
                try:
                    if issubclass(obj, self.valid_type):
                        return True
                except:
                    pass
                return False
            else:
                if isinstance(obj, self.valid_type):
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
        keys = dict()
        for key, value in cls.__dict__.items():
            if not isinstance(value, Key):
                continue
            assert key == value, f"The name of a key in a keyring must match the variable's name; varname: {key}, value: {value}"
            keys[key] = value
        return keys

    @classmethod
    def get_key_by_matching_string(cls, key_str: str) -> Key:
        try:
            return cls.__dict__[key_str]
        except KeyError:
            raise KeyError(f"Failed to get matching key for string: {key_str}. "
                           f"It doesn't appear to exist in the keyring: {cls.get_keys_in_keyring()}")
