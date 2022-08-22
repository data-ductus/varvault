import abc


class VaultStructBase(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def create(cls, vault_key, vault_value):
        raise NotImplementedError(f"{cls.create.__name__} was not implemented in the subclass that inherited this.")


class VaultStructDictBase(VaultStructBase, dict, abc.ABC):

    def __setattr__(self, key, value):
        super(VaultStructDictBase, self).__setattr__(key, value)
        super(VaultStructDictBase, self).__setitem__(key, value)


class VaultStructListBase(VaultStructBase, list, abc.ABC):
    pass


class VaultStructStringBase(VaultStructBase, str, abc.ABC):
    pass


class VaultStructIntBase(VaultStructBase, int, abc.ABC):
    pass


class VaultStructFloatBase(VaultStructBase, float, abc.ABC):
    pass
