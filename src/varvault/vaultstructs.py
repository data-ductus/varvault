import abc


class VaultStructBase(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def build_from_vault_key(cls, vault_key, vault_value):
        pass


class VaultStructDictBase(VaultStructBase, dict):
    @classmethod
    @abc.abstractmethod
    def build_from_vault_key(cls, vault_key, vault_value):
        pass

    def __setattr__(self, key, value):
        super(VaultStructDictBase, self).__setattr__(key, value)
        super(VaultStructDictBase, self).__setitem__(key, value)


class VaultStructListBase(VaultStructBase, list):
    @classmethod
    @abc.abstractmethod
    def build_from_vault_key(cls, vault_key, vault_value):
        pass


class VaultStructStringBase(VaultStructBase, str):
    @classmethod
    @abc.abstractmethod
    def build_from_vault_key(cls, vault_key, vault_value):
        pass


class VaultStructIntBase(VaultStructBase, int):
    @classmethod
    @abc.abstractmethod
    def build_from_vault_key(cls, vault_key, vault_value):
        pass


class VaultStructFloatBase(VaultStructBase, float):
    @classmethod
    @abc.abstractmethod
    def build_from_vault_key(cls, vault_key, vault_value):
        pass
