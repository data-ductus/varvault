from typing import *

from varvault.keyring import Key


class MiniVault(dict):
    """Class that acts as a very bare-bones vault to represent variables either coming from the vault via get_multiple, or when returning variables form a vaulted function."""

    def __init__(self, d=None, **kwargs):
        if d is None:
            super(MiniVault, self).__init__(kwargs)
        else:
            super(MiniVault, self).__init__(d)

    @staticmethod
    def build(keys: List[Key] or Tuple[Key], values: List[Any] or Tuple[Any]):
        assert isinstance(keys, (list, tuple)), "'keys' must be a list or a tuple"
        assert isinstance(values, (list, tuple)), "'values' must be a list or a tuple"

        assert len(keys) == len(values), "The length of 'keys' and 'values' must be identical"

        data = dict()
        for i in range(len(keys)):
            key = keys[i]
            value = values[i]
            assert isinstance(key, Key), f"Key {key} is not of correct type {Key}"
            assert key.type_is_valid(value), f"Key '{key}' requires type to be '{key.valid_type}', but type for value is '{type(value)}'. " \
                                             f"Is the order of your keys and values passed to '{MiniVault.build.__name__}' wrong?"
            data[key] = value
        return MiniVault(data)
