from __future__ import annotations

import abc
from typing import Any


class VaultStructBase(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def create(cls, vault_key: str, vault_value: Any) -> VaultStructBase:
        """
        Creates a new instance of the class that inherits this.

        :param vault_key: The key as it is written in the vault
        :param vault_value: The value as it is written in the vault
        :return: A new instance of the class that inherits this
        """
        raise NotImplementedError(f"{cls.create.__name__} was not implemented in the subclass that inherited this.")


class VaultStructDictBase(VaultStructBase, dict, abc.ABC):
    """
    This class is used to create a set dict is stored in the vault.
    The primary use would be to create your own type of dict which have some special functions on it, while saving all the values in the dict in the vault.
    Using this to create your own complex types is highly recommended.
    """
    def __setattr__(self, key, value):
        super(VaultStructDictBase, self).__setattr__(key, value)
        super(VaultStructDictBase, self).__setitem__(key, value)

    def __setitem__(self, key, value):
        super(VaultStructDictBase, self).__setattr__(key, value)
        super(VaultStructDictBase, self).__setitem__(key, value)


class VaultStructListBase(VaultStructBase, list, abc.ABC):
    """
    This class is used to create a set list is stored in the vault.
    The primary use would be to create your own type of list which have some special functions on it, while saving all the values in the list in the vault.
    """
    def __setattr__(self, key, value):
        super(VaultStructListBase, self).__setattr__(key, value)
        if value not in self:
            self.append(value)


class VaultStructSetBase(VaultStructBase, set, abc.ABC):
    """
    This class is used to create a set that is stored in the vault.
    The primary use would be to create your own type of set which have some special functions on it, while saving all the values in the set in the vault.
    """
    def __setattr__(self, key, value):
        super(VaultStructSetBase, self).__setattr__(key, value)
        self.add(value)


class VaultStructStringBase(VaultStructBase, str, abc.ABC):
    """
    This class is used to create a string that is stored in the vault.
    The primary use would be to create your own type of string which have some special functions on it.
    """
    pass


class VaultStructIntBase(VaultStructBase, int, abc.ABC):
    """
    This class is used to create an integer that is stored in the vault.
    The primary use would be to create your own type of integer which have some special functions on it.
    """
    pass


class VaultStructFloatBase(VaultStructBase, float, abc.ABC):
    """
    This class is used to create a float that is stored in the vault.
    The primary use would be to create your own type of float which have some special functions on it.
    """
    pass
