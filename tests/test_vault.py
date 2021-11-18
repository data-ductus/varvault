import os
import sys
import json
import pytest
import logging
import tempfile


DIR = os.path.dirname(os.path.realpath(__file__))
path = f"{os.path.dirname(DIR)}"
temp_path = [path]
temp_path.extend(sys.path)
sys.path = temp_path

import varvault

logger = logging.getLogger("pytest")


vault_file_new = f"{DIR}/new-vault.json"
vault_file_new_secondary = f"{DIR}/new-vault-secondary.json"
existing_vault = f"{DIR}/existing-vault.json"
faulty_existing_vault = f"{DIR}/faulty-existing-vault.json"
faulty_vault_key_missmatch = f"{DIR}/faulty-vault-key-missmatch.json"


class Keyring(varvault.Keyring):
    key_valid_type_is_str = varvault.Key("key_valid_type_is_str", valid_type=str)
    key_valid_type_is_int = varvault.Key("key_valid_type_is_int", valid_type=int)


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
    def build_from_vault_key(cls, vault_key, vault_value):
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
    def build_from_vault_key(cls, vault_key, vault_value):
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
    def build_from_vault_key(cls, vault_key, vault_value):
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
    def build_from_vault_key(cls, vault_key, vault_value):
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
    def build_from_vault_key(cls, vault_key, vault_value):
        obj = VaultStructInt(int_value=vault_value, extra_value="extra_value-cannot-possibly-be-saved-to-an-int")
        return obj


class KeyringVaultStruct(varvault.Keyring):
    key_vault_struct_dict = varvault.Key("key_vault_struct_dict", VaultStructDict)
    key_vault_struct_list = varvault.Key("key_vault_struct_list", VaultStructList)
    key_vault_struct_string = varvault.Key("key_vault_struct_string", VaultStructString)
    key_vault_struct_float = varvault.Key("key_vault_struct_float", VaultStructFloat)
    key_vault_struct_int = varvault.Key("key_vault_struct_int", VaultStructInt)


class TestVault:

    @classmethod
    def setup_class(cls):
        logger.info(tempfile.tempdir)
        tempfile.tempdir = "/tmp" if sys.platform == "darwin" or sys.platform == "linux" else tempfile.gettempdir()
        logger.info(tempfile.tempdir)

    def test_assert_true(self):
        assert True
        logger.info(DIR)

    def test_create_new_vault(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new)

        @vault.vaulter(return_keys=Keyring.key_valid_type_is_str)
        def _set_valid():
            return "valid-key"

        _set_valid()
        assert vault.get(Keyring.key_valid_type_is_str) == "valid-key"

        @vault.vaulter(return_keys=Keyring.key_valid_type_is_int)
        def _set_invalid():
            return "invalid-key; must be int"

        try:
            _set_invalid()
            pytest.fail(f"Somehow managed to set an invalid value to key {Keyring.key_valid_type_is_int} (valid type: {Keyring.key_valid_type_is_int.valid_type})")
        except Exception as e:
            assert "Key 'key_valid_type_is_int' requires type to be '<class 'int'>'" in str(e), f"Unexpected error: {e}"
            logger.info(f"Expected error received; test passed")
            assert Keyring.key_valid_type_is_int not in vault

    def test_put(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new)
        mv = varvault.MiniVault({Keyring.key_valid_type_is_str: "value", Keyring.key_valid_type_is_int: 1})
        vault.vault.put(mv)
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int in vault

        vault = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new)
        vault.vault.put(Keyring.key_valid_type_is_str, "value")
        assert Keyring.key_valid_type_is_str in vault

    def test_create_from_vault(self):
        vault = varvault.from_vault(Keyring, "from-vault", existing_vault)
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int in vault
        assert vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert vault.get(Keyring.key_valid_type_is_int) == 1
        d = json.load(open(existing_vault))
        assert Keyring.key_valid_type_is_str in d and Keyring.key_valid_type_is_int in d, "It appears that loading from the vault file has cleared the vault file unintentionally. This is very bad"

    def test_load_from_one_write_to_another(self):
        vault = varvault.from_vault(Keyring, "from-vault", existing_vault, varvault_vault_filename_to=vault_file_new)

        @vault.vaulter(varvault.VaultFlags.permit_modifications(), input_keys=Keyring.key_valid_type_is_str, return_keys=Keyring.key_valid_type_is_str)
        def mod(**kwargs):
            key_valid_type_is_str = kwargs.get(Keyring.key_valid_type_is_str)
            assert key_valid_type_is_str == "valid"
            modded = f"modded"
            return modded
        mod()

        assert vault.get(Keyring.key_valid_type_is_str) == "modded"
        assert json.load(open(vault_file_new)).get(Keyring.key_valid_type_is_str) == "modded", f"The value for {Keyring.key_valid_type_is_str} in vault_filename_to is not the expected"
        assert json.load(open(existing_vault)).get(Keyring.key_valid_type_is_str) == "valid", f"The value for {Keyring.key_valid_type_is_str} in vault_filename_from has changed. This is very bad"

    def test_permit_modifications(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new)
        vault.insert(Keyring.key_valid_type_is_str, "valid")
        try:
            @vault.vaulter(return_keys=Keyring.key_valid_type_is_str)
            def _set():
                return "new-value-that-should-not-go-in"
            _set()

            pytest.fail("Managed to set a new value to an existing key while modifications are not permitted")
        except Exception as e:
            assert "Keys ['key_valid_type_is_str'] are already in the vault and permit_modifications is not set." in str(e), f"Unexpected error: {e}"
            logger.info(f"Expected error received; test passed")
            assert vault.get(Keyring.key_valid_type_is_str) == "valid", f"Value for {Keyring.key_valid_type_is_str} is not what it should be"

        @vault.vaulter(varvault.VaultFlags.permit_modifications(), return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "new-modified-value"
        _set()

        assert vault.get(Keyring.key_valid_type_is_str) == "new-modified-value", f"Value for {Keyring.key_valid_type_is_str} is not what it should be"

        new_vault = varvault.from_vault(Keyring, "from-vault", vault_file_new, varvault.VaultFlags.permit_modifications())

        @new_vault.vaulter(return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "new-modified-value-gen-2"
        _set()

        assert new_vault.get(Keyring.key_valid_type_is_str) == "new-modified-value-gen-2", f"Value for {Keyring.key_valid_type_is_str} is not what it should be"

    def test_create_readonly_vault(self):
        vault = varvault.from_vault(Keyring, "from-vault", existing_vault, varvault.VaultFlags.file_is_read_only())
        try:
            vault.insert(Keyring.key_valid_type_is_int, 1)
            pytest.fail("Insert: Somehow managed to insert a value into a vault that is supposed to be read-only")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        try:
            @vault.vaulter(return_keys=Keyring.key_valid_type_is_int)
            def _set():
                return 1
            _set()

            pytest.fail("Vaulter: Somehow managed to insert a value into a vault that is supposed to be read-only")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

    def test_read_only_key_not_in_keyring(self):
        json.dump({Keyring.key_valid_type_is_str: "valid", Keyring.key_valid_type_is_int: 1, "temp": "this-should-not-be-in-the-vault"}, open(vault_file_new, "w"))
        vault = varvault.from_vault(Keyring, "from-vault", vault_file_new, varvault.VaultFlags.file_is_read_only())
        assert varvault.Key("temp") not in vault, "Vault contains a key that should not be in the vault since if doesn't exist in the keyring"
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int in vault

    def test_insert_nonexistent_key(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new)
        temp_key = varvault.Key("temp_key")
        try:
            vault.insert(temp_key, "this-should-not-go-in")
            pytest.fail("Somehow managed to insert a non-existent key into a vault that should not permit this")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

    def test_create_from_faulty_vault(self):
        this_key_doesnt_exist_in_keyring = varvault.Key("this_key_doesnt_exist_in_keyring", valid_type=str)
        try:
            vault = varvault.from_vault(Keyring, "from-vault", faulty_existing_vault)
            pytest.fail("Managed to create a vault from a file that should be faulty")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        try:
            vault = varvault.from_vault(Keyring, "from-vault", faulty_vault_key_missmatch)
            pytest.fail("Managed to create a vault from a file with a key not in keyring, and ignore_keys_not_in_keyring is False")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        vault = varvault.from_vault(Keyring, "from-vault", faulty_vault_key_missmatch, varvault.VaultFlags.ignore_keys_not_in_keyring(), varvault_vault_filename_to=vault_file_new)
        assert this_key_doesnt_exist_in_keyring not in vault, f"Key {this_key_doesnt_exist_in_keyring} was found in the vault when it shouldn't be"

        vault = varvault.from_vault(Keyring, "from-vault", faulty_vault_key_missmatch,
                                    varvault_vault_filename_to=vault_file_new,
                                    this_key_doesnt_exist_in_keyring=this_key_doesnt_exist_in_keyring)
        assert this_key_doesnt_exist_in_keyring in vault, f"Key {this_key_doesnt_exist_in_keyring} was not found in the vault when it should be added as an extra key"

    def test_insert_type_validation(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new)
        try:
            vault.insert(Keyring.key_valid_type_is_int, "this-should-not-work")
            assert False, "Somehow managed to insert a value for a key that should not work"
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

    def test_vault_struct_dict(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_vault_filename_to=vault_file_new)

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_dict)
        def _set():
            return VaultStructDict("v1", 1)

        _set()
        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_dict), VaultStructDict)
        logger.info(vault.get(KeyringVaultStruct.key_vault_struct_dict))

        from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", vault_file_new)
        assert isinstance(from_vault.get(KeyringVaultStruct.key_vault_struct_dict), VaultStructDict)
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_dict), "internal_function")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_dict), "value_1")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_dict), "value_2")

    def test_vault_struct_list(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_vault_filename_to=vault_file_new)

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_list)
        def _set():
            return VaultStructList("v1", 1)

        _set()
        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_list), VaultStructList)
        logger.info(vault.get(KeyringVaultStruct.key_vault_struct_list))

        from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", vault_file_new)
        assert isinstance(from_vault.get(KeyringVaultStruct.key_vault_struct_list), VaultStructList)
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_list), "internal_function")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_list), "value_1")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_list), "value_2")

    def test_vault_struct_string(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_vault_filename_to=vault_file_new)

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_string)
        def _set():
            return VaultStructString("string-value", "extra-value-here")

        _set()
        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_string), VaultStructString)
        logger.info(vault.get(KeyringVaultStruct.key_vault_struct_string))

        from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", vault_file_new)
        assert isinstance(from_vault.get(KeyringVaultStruct.key_vault_struct_string), VaultStructString)
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_string), "internal_function")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_string), "string_value")

    def test_vault_struct_float(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_vault_filename_to=vault_file_new)

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_float)
        def _set():
            return VaultStructFloat(3.14, "extra-value-here")

        _set()
        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_float), VaultStructFloat)
        logger.info(vault.get(KeyringVaultStruct.key_vault_struct_float))

        from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", vault_file_new)
        assert isinstance(from_vault.get(KeyringVaultStruct.key_vault_struct_float), VaultStructFloat)
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_float), "internal_function")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_float), "float_value")

    def test_vault_struct_int(self):
        vault = varvault.create_vault(KeyringVaultStruct, "vault", varvault_vault_filename_to=vault_file_new)

        @vault.vaulter(return_keys=KeyringVaultStruct.key_vault_struct_int)
        def _set():
            return VaultStructInt(1, "extra-value-here")
        _set()

        assert isinstance(vault.get(KeyringVaultStruct.key_vault_struct_int), VaultStructInt)
        logger.info(vault.get(KeyringVaultStruct.key_vault_struct_int))

        from_vault = varvault.from_vault(KeyringVaultStruct, "from-vault", vault_file_new)
        assert isinstance(from_vault.get(KeyringVaultStruct.key_vault_struct_int), VaultStructInt)
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_int), "internal_function")
        assert hasattr(from_vault.get(KeyringVaultStruct.key_vault_struct_int), "int_value")

    def test_live_update_vault(self):
        vault_new = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new)
        vault_from = varvault.from_vault(Keyring, "vault-from", vault_file_new, varvault.VaultFlags.live_update(), varvault.VaultFlags.file_is_read_only())

        @vault_new.vaulter(return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert Keyring.key_valid_type_is_str not in vault_from, f"{Keyring.key_valid_type_is_str} already in the vault; This should not be the case"

        @vault_from.vaulter(input_keys=Keyring.key_valid_type_is_str)
        def _get(**kwargs):
            v = kwargs.get(Keyring.key_valid_type_is_str)
            assert v == "valid", f"Value {v} is not correct; Live-update doesn't work"
        _get()

    def test_clean_return_keys(self):
        vault_new = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new)

        @vault_new.vaulter(return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert vault_new.get(Keyring.key_valid_type_is_str) == "valid"

        @vault_new.vaulter(varvault.VaultFlags.clean_return_var_keys(), return_keys=Keyring.key_valid_type_is_str)
        def _clean():
            return

        _clean()
        assert Keyring.key_valid_type_is_str in vault_new, f"No {Keyring.key_valid_type_is_str} in vault"
        assert vault_new.get(Keyring.key_valid_type_is_str) == "", f"Key {Keyring.key_valid_type_is_str} is not an empty string; {vault_new.get(Keyring.key_valid_type_is_str)}"

    def test_extra_keys(self):
        extra_key1 = varvault.Key("extra_key1", valid_type=dict)
        vault_new = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new, extra_key1=varvault.Key("extra_key1", valid_type=dict))

        @vault_new.vaulter(return_keys=extra_key1)
        def _set_invalid():
            return [1, 2, 3]
        try:
            _set_invalid()
            pytest.fail("Unexpectedly managed to set an invalid value to an extra key")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        @vault_new.vaulter(return_keys=extra_key1)
        def _set_valid():
            return {"a": 1, "b": 2, "c": 3}
        _set_valid()

        @vault_new.vaulter(varvault.VaultFlags.clean_return_var_keys(), return_keys=extra_key1)
        def _clean():
            return
        _clean()

        assert vault_new.get(extra_key1) == {}

    def test_return_tuple_is_single_item(self):
        tuple_item = varvault.Key("tuple_item", valid_type=tuple)
        vault = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new, tuple_item=tuple_item)

        @vault.vaulter(varvault.VaultFlags.return_tuple_is_single_item(), return_keys=tuple_item)
        def _set():
            return 1, 2, 3
        _set()

        assert tuple_item in vault, f"Flag: No {tuple_item} found in vault"
        assert vault.get(tuple_item) == (1, 2, 3), "Flag: missmatch"

        vault = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new, tuple_item=tuple_item)

        @vault.vaulter(return_keys=tuple_item)
        def _set():
            return 1, 2, 3
        _set()

        assert tuple_item in vault, f"No flag: No {tuple_item} found in vault"
        assert vault.get(tuple_item) == (1, 2, 3), "No flag: Missmatch"

    def test_split_return_keys(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new)
        vault_secondary = varvault.create_vault(Keyring, "vault-secondary", varvault_vault_filename_to=vault_file_new_secondary)

        @vault.vaulter(varvault.VaultFlags.split_return_keys(), return_keys=Keyring.key_valid_type_is_str)
        @vault_secondary.vaulter(varvault.VaultFlags.split_return_keys(), return_keys=Keyring.key_valid_type_is_int)
        def _set():
            return varvault.MiniVault({Keyring.key_valid_type_is_str: "valid", Keyring.key_valid_type_is_int: 1})
        _set()

        assert Keyring.key_valid_type_is_str in vault and Keyring.key_valid_type_is_int not in vault
        assert Keyring.key_valid_type_is_int in vault_secondary and Keyring.key_valid_type_is_str not in vault_secondary

        assert vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert vault_secondary.get(Keyring.key_valid_type_is_int) == 1


class TestLogging:
    @classmethod
    def setup_class(cls):
        tempfile.tempdir = "/tmp" if sys.platform == "darwin" or sys.platform == "linux" else tempfile.gettempdir()

    def test_silent(self):
        temp_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault-stream.log")
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault.log")
        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.silent(), varvault_vault_filename_to=vault_file_new)
        vault_new.logger.addHandler(logging.StreamHandler(open(temp_log_file, "w")))

        @vault_new.vaulter(return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()
        assert len(open(temp_log_file).readlines()) <= 2, f"There appears to be more lines in the log file than what there should be. " \
                                                          f"There should only be 2 at most. {varvault.VaultFlags.silent()} appears to not function correctly"
        assert len(open(vault_log_file).readlines()) <= 2, f"There appears to be more lines in the log file than what there should be. " \
                                                           f"There should only be 2 at most. {varvault.VaultFlags.silent()} appears to not function correctly"

    def test_debug(self):
        temp_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault-stream.log")
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault.log")
        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.debug(), varvault_vault_filename_to=vault_file_new)
        # Create and set a file to act as a StreamHandler for the logger object in varvault.
        # This way, we can easily capture stdout to a file and assert that the output is the expected
        vault_new.logger.addHandler(logging.StreamHandler(open(temp_log_file, "w")))

        @vault_new.vaulter(return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert len(open(temp_log_file).readlines()) >= 10, f"There appears to be fewer lines in the log file than what there should be. " \
                                                           f"There should only be 12 at least. {varvault.VaultFlags.debug()} appears to not function correctly"
        assert len(open(vault_log_file).readlines()) >= 12, f"There appears to be fewer lines in the log file than what there should be. " \
                                                            f"There should only be 12 at least. {varvault.VaultFlags.debug()} appears to not function correctly"

    def test_silent_and_debug(self):
        temp_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault-stream.log")
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault.log")
        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.debug(), varvault_vault_filename_to=vault_file_new)
        # Create and set a file to act as a StreamHandler for the logger object in varvault.
        # This way, we can easily capture stdout to a file and assert that the output is the expected
        vault_new.logger.addHandler(logging.StreamHandler(open(temp_log_file, "w")))

        @vault_new.vaulter(varvault.VaultFlags.silent(), return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert len(open(temp_log_file).readlines()) == 0, f"There appears to be more lines in the log file than what there should be. " \
                                                          f"There should be 0 at most. {varvault.VaultFlags.debug()} with {varvault.VaultFlags.silent()} appears to not function correctly"
        assert len(open(vault_log_file).readlines()) == 12, f"There appears to be fewer lines in the log file than what there should be. " \
                                                            f"There should be 12 at most. {varvault.VaultFlags.debug()} with {varvault.VaultFlags.silent()} appears to not function correctly"

    def test_disable_logger(self):
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault.log")
        try:
            os.unlink(vault_log_file)
        except OSError:
            pass
        assert not os.path.exists(vault_log_file), f"{vault_log_file} still exists, weird"

        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.disable_logger(), varvault_vault_filename_to=vault_file_new)
        assert vault_new.logger is None, "logger object is not None; it should be"
        assert not os.path.exists(vault_log_file), f"{vault_log_file} exists after creating the vault when saying there shouldn't be a logger object"

        @vault_new.vaulter(varvault.VaultFlags.silent(), return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()
        assert not os.path.exists(vault_log_file), f"{vault_log_file} exists after using the vault. How?!"

    def test_remove_existing_log_file(self):
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault.log")
        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.debug(), varvault_vault_filename_to=vault_file_new)

        @vault_new.vaulter(varvault.VaultFlags.silent(), return_keys=Keyring.key_valid_type_is_str)
        def _doset():
            return "valid"
        _doset()
        with open(vault_log_file) as f1:
            assert len(f1.readlines()) == 12, f"There should be exactly 12 lines in the log-file."
        vault_from = varvault.from_vault(Keyring, "vault", vault_file_new, varvault.VaultFlags.remove_existing_log_file())
        assert Keyring.key_valid_type_is_str in vault_from
        with open(vault_log_file) as f2:
            assert len(f2.readlines()) == 3, f"There should be exactly 3 lines in the logfile. It seems the log-file wasn't removed when the new vault was created from the existing vault."

    def test_specific_logger(self):
        old_handlers = logger.handlers.copy()
        temp_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "pytest-stream.log")
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "pytest-file.log")
        try:
            os.unlink(temp_log_file)
        except OSError:
            pass
        try:
            os.unlink(vault_log_file)
        except OSError:
            pass

        try:
            logger.handlers.clear()
            logger.addHandler(logging.StreamHandler(open(temp_log_file, "w")))
            logger.addHandler(logging.FileHandler(filename=vault_log_file))

            vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.debug(), varvault_vault_filename_to=vault_file_new, varvault_specific_logger=logger)
            assert vault_new.logger.name == "pytest"  # The logger used for pytest here is called pytest

            @vault_new.vaulter(varvault.VaultFlags.silent(), return_keys=Keyring.key_valid_type_is_str)
            def _set():
                return "valid"
            _set()

            assert len(open(temp_log_file).readlines()) == 1, f"There appears to be more lines in the log file than what there should be. There should be 1 at most."
            assert len(open(vault_log_file).readlines()) == 11, f"There appears to be fewer lines in the log file than what there should be. There should be 11 at most."
        finally:
            logger.handlers.clear()
            logger.handlers = old_handlers
