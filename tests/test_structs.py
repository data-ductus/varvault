from commons import *


vault_file_new = f"{DIR}/new-vault.json"


class VaultStructDict(varvault.VaultStructDictBase):
    def __init__(self, value_1: str, value_2: int, **kwargs):
        super(VaultStructDict, self).__init__(**kwargs)
        assert isinstance(value_1, str)
        assert isinstance(value_2, int)

        self.value_1 = value_1
        self.value_2 = value_2

    def internal_function(self):
        pass

    @classmethod
    def create(cls, vault_key, vault_value):
        obj = VaultStructDict(**vault_value)
        return obj


class VaultStructList(varvault.VaultStructListBase):
    def __init__(self, value_1: str, value_2: int, *args):
        super(VaultStructList, self).__init__(*args)
        assert isinstance(value_1, str)
        assert isinstance(value_2, int)

        self.value_1 = value_1
        self.value_2 = value_2

        self.extend([value_1, value_2])

    def internal_function(self):
        pass

    @classmethod
    def create(cls, vault_key, vault_value):
        obj = VaultStructList(*vault_value)
        return obj


class VaultStructString(varvault.VaultStructStringBase):
    def __new__(cls, string_value, extra_value, *args, **kwargs):
        assert isinstance(string_value, str)
        obj = super().__new__(cls, string_value)
        obj.string_value = string_value
        obj.extra_value = extra_value
        return obj

    def internal_function(self):
        pass

    @classmethod
    def create(cls, vault_key, vault_value):
        obj = VaultStructString(string_value=vault_value, extra_value="extra_value-cannot-possibly-be-saved-to-a-string")
        return obj


class VaultStructFloat(varvault.VaultStructFloatBase):
    def __new__(cls, float_value, extra_value, *args, **kwargs):
        assert isinstance(float_value, float)
        obj = super().__new__(cls, float_value)
        obj.float_value = float_value
        obj.extra_value = extra_value
        return obj

    def internal_function(self):
        pass

    @classmethod
    def create(cls, vault_key, vault_value):
        obj = VaultStructFloat(float_value=vault_value, extra_value="extra_value-cannot-possibly-be-saved-to-a-float")
        return obj


class VaultStructInt(varvault.VaultStructIntBase):
    def __new__(cls, int_value, extra_value, *args, **kwargs):
        assert isinstance(int_value, int)
        obj = super().__new__(cls, int_value)
        obj.int_value = int_value
        obj.extra_value = extra_value
        return obj

    def internal_function(self):
        pass

    @classmethod
    def create(cls, vault_key, vault_value):
        obj = VaultStructInt(int_value=vault_value, extra_value="extra_value-cannot-possibly-be-saved-to-an-int")
        return obj


class VaultStructDictInvalid(varvault.VaultStructDictBase):
    # This struct should fail to be loaded from a file since "build_from_vault_key" is not implemented.

    def __init__(self, value_1: str, value_2: int, **kwargs):
        super(VaultStructDictInvalid, self).__init__(**kwargs)
        assert isinstance(value_1, str)
        assert isinstance(value_2, int)

        self.value_1 = value_1
        self.value_2 = value_2


class KeyringVaultStruct(varvault.Keyring):
    key_vault_struct_dict = varvault.Key("key_vault_struct_dict", valid_type=VaultStructDict)
    key_vault_struct_list = varvault.Key("key_vault_struct_list", valid_type=VaultStructList)
    key_vault_struct_string = varvault.Key("key_vault_struct_string", valid_type=VaultStructString)
    key_vault_struct_float = varvault.Key("key_vault_struct_float", valid_type=VaultStructFloat)
    key_vault_struct_int = varvault.Key("key_vault_struct_int", valid_type=VaultStructInt)
    key_vault_struct_dict_invalid = varvault.Key("key_vault_struct_dict_invalid", valid_type=VaultStructDictInvalid)


class TestVaultStructs:
    def setup_method(self):
        try:
            os.remove(vault_file_new)
        except:
            pass

    def test_vault_struct_dict(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_resource_to=varvault.JsonResource(vault_file_new))

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_dict)
        def _set():
            return VaultStructDict("v1", 1)

        _set()
        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_dict), VaultStructDict)
        logger.info(vault.get(KeyringVaultStruct.key_vault_struct_dict))

        from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", varvault.JsonResource(vault_file_new))
        assert isinstance(from_vault.get(KeyringVaultStruct.key_vault_struct_dict), VaultStructDict)
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_dict), "internal_function")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_dict), "value_1")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_dict), "value_2")

    def test_vault_struct_list(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_resource_to=varvault.JsonResource(vault_file_new))

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_list)
        def _set():
            return VaultStructList("v1", 1)

        _set()
        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_list), VaultStructList)
        logger.info(vault.get(KeyringVaultStruct.key_vault_struct_list))

        from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", varvault.JsonResource(vault_file_new))
        assert isinstance(from_vault.get(KeyringVaultStruct.key_vault_struct_list), VaultStructList)
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_list), "internal_function")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_list), "value_1")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_list), "value_2")

    def test_vault_struct_string(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_resource_to=varvault.JsonResource(vault_file_new))

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_string)
        def _set():
            return VaultStructString("string-value", "extra-value-here")

        _set()
        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_string), VaultStructString)
        logger.info(vault.get(KeyringVaultStruct.key_vault_struct_string))

        from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", varvault.JsonResource(vault_file_new))
        assert isinstance(from_vault.get(KeyringVaultStruct.key_vault_struct_string), VaultStructString)
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_string), "internal_function")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_string), "string_value")

    def test_vault_struct_float(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_resource_to=varvault.JsonResource(vault_file_new))

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_float)
        def _set():
            return VaultStructFloat(3.14, "extra-value-here")

        _set()
        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_float), VaultStructFloat)
        logger.info(vault.get(KeyringVaultStruct.key_vault_struct_float))

        from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", varvault.JsonResource(vault_file_new))
        assert isinstance(from_vault.get(KeyringVaultStruct.key_vault_struct_float), VaultStructFloat)
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_float), "internal_function")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_float), "float_value")

    def test_vault_struct_int(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_resource_to=varvault.JsonResource(vault_file_new))

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_int)
        def _set():
            return VaultStructInt(1, "extra-value-here")
        _set()

        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_int), VaultStructInt)
        logger.info(vault.get(KeyringVaultStruct.key_vault_struct_int))

        from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", varvault.JsonResource(vault_file_new))
        assert isinstance(from_vault.get(KeyringVaultStruct.key_vault_struct_int), VaultStructInt)
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_int), "internal_function")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_int), "int_value")

    def test_invalid_vault_struct(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_resource_to=varvault.JsonResource(vault_file_new))

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_dict_invalid)
        def _set():
            return VaultStructDictInvalid("v1", 1)

        _set()
        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_dict_invalid), VaultStructDictInvalid)
        try:
            from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", varvault.JsonResource(vault_file_new))
            assert False, "Managed to create a vault with a VaultStruct that hasn't been implemented correctly"
        except NotImplementedError as e:
            logger.info(f"Expected error {e}: failed to load vault with key as invalid VaultStruct")

