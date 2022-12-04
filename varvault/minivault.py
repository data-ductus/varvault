from typing import *

from .utils import assert_and_raise
from .keyring import Key


class MiniVault(dict):
    """Class that acts as a very bare-bones vault to represent variables either coming from the vault via get_multiple, or when returning variables form a vaulted function."""

    def __init__(self, d=None, **kwargs):
        d = d or {}
        super(MiniVault, self).__init__(d, **kwargs)

    @staticmethod
    def build(keys: List[Key] or Tuple[Key], values: List[Any] or Tuple[Any]):
        f"""Builds a {MiniVault}-object based on iterables of {keys} and {values}. Note that the number of {keys} and the number of {values} must be identical"""
        assert isinstance(keys, (list, tuple)), f"'keys' must be a list or a tuple, not {type(keys)}"
        assert isinstance(values, (list, tuple)), f"'values' must be a list or a tuple, not {type(values)}"

        assert len(keys) == len(values), "The length of 'keys' and 'values' must be identical"

        data = dict()
        for i in range(len(keys)):
            key = keys[i]
            value = values[i]
            assert isinstance(key, Key), f"Key {key} is not of correct type {Key}"
            assert_and_raise(key.type_is_valid(value), ValueError(f"Key '{key}' requires type to be '{key.valid_type}', but type for value is '{type(value)}'. "
                                                                  f"Is the order of your keys and values passed to '{MiniVault.build.__name__}' wrong?"))
            data[key] = value

        return MiniVault(data)

    def add(self, k, v):
        """Adds a value mapped to a key. Essentially just wraps the '__setitem__' function."""
        self.__setitem__(k, v)

    def keys(self) -> List[Key]:
        """Returns a list of keys"""
        return list(super(MiniVault, self).keys())

    def values(self) -> List[Any]:
        """Returns a list of values"""
        return list(super(MiniVault, self).values())
