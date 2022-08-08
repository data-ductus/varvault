import json
import threading

import pytest
import tempfile

from commons import *


vault_file_new = f"{DIR}/new-vault.json"
vault_file_new_secondary = f"{DIR}/new-vault-secondary.json"
existing_vault = f"{DIR}/existing-vault.json"
faulty_existing_vault = f"{DIR}/faulty-existing-vault.json"
faulty_vault_key_missmatch = f"{DIR}/faulty-vault-key-missmatch.json"


class TestVault:

    @classmethod
    def setup_class(cls):
        logger.info(tempfile.tempdir)
        tempfile.tempdir = "/tmp" if sys.platform == "darwin" or sys.platform == "linux" else tempfile.gettempdir()
        logger.info(tempfile.tempdir)

    def setup_method(self):
        try:
            os.remove(vault_file_new)
        except:
            pass
        try:
            os.remove(vault_file_new_secondary)
        except:
            pass

    def test_create_new_vault(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))

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
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        mv = varvault.MiniVault({Keyring.key_valid_type_is_str: "value", Keyring.key_valid_type_is_int: 1})
        vault.vault.put(mv)
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int in vault

        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        vault.vault.put(Keyring.key_valid_type_is_str, "value")
        assert Keyring.key_valid_type_is_str in vault

    def test_create_from_vault(self):
        vault = varvault.from_vault(Keyring, "from-vault", varvault.JsonFilehandler(existing_vault))
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int in vault
        assert vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert vault.get(Keyring.key_valid_type_is_int) == 1
        d = json.load(open(existing_vault))
        assert Keyring.key_valid_type_is_str in d and Keyring.key_valid_type_is_int in d, "It appears that loading from the vault file has cleared the vault file unintentionally. This is very bad"

    def test_load_from_one_write_to_another(self):
        vault = varvault.from_vault(Keyring, "from-vault", varvault.JsonFilehandler(existing_vault), varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))

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

    def test_create_from_vault_no_valid_type_in_key(self):
        class KeyringTemp(varvault.Keyring):
            key_valid_type_is_str = varvault.Key("key_valid_type_is_str")
            key_valid_type_is_int = varvault.Key("key_valid_type_is_int")

        vault = varvault.from_vault(KeyringTemp, "from-vault", varvault.JsonFilehandler(existing_vault), varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))

    def test_permit_modifications(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        vault.insert(Keyring.key_valid_type_is_str, "valid")
        try:
            @vault.vaulter(return_keys=Keyring.key_valid_type_is_str)
            def _set():
                return "new-value-that-should-not-go-in"
            _set()

            pytest.fail("Managed to set a new value to an existing key while modifications are not permitted")
        except Exception as e:
            logger.info(f"Expected error received; test passed")
            assert vault.get(Keyring.key_valid_type_is_str) == "valid", f"Value for {Keyring.key_valid_type_is_str} is not what it should be"

        @vault.vaulter(varvault.VaultFlags.permit_modifications(), return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "new-modified-value"
        _set()

        assert vault.get(Keyring.key_valid_type_is_str) == "new-modified-value", f"Value for {Keyring.key_valid_type_is_str} is not what it should be"

        new_vault = varvault.from_vault(Keyring, "from-vault", varvault.JsonFilehandler(vault_file_new), varvault.VaultFlags.permit_modifications())

        @new_vault.vaulter(return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "new-modified-value-gen-2"
        _set()

        assert new_vault.get(Keyring.key_valid_type_is_str) == "new-modified-value-gen-2", f"Value for {Keyring.key_valid_type_is_str} is not what it should be"

    def test_create_readonly_vault(self):
        vault = varvault.from_vault(Keyring, "from-vault", varvault.JsonFilehandler(existing_vault), varvault.VaultFlags.vault_is_read_only())
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
        vault = varvault.from_vault(Keyring, "from-vault", varvault.JsonFilehandler(existing_vault), varvault.VaultFlags.vault_is_read_only())
        assert varvault.Key("temp") not in vault, "Vault contains a key that should not be in the vault since if doesn't exist in the keyring"
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int in vault

    def test_insert_nonexistent_key(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        temp_key = varvault.Key("temp_key")
        try:
            vault.insert(temp_key, "this-should-not-go-in")
            pytest.fail("Somehow managed to insert a non-existent key into a vault that should not permit this")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

    def test_create_from_faulty_vault(self):
        this_key_doesnt_exist_in_keyring = varvault.Key("this_key_doesnt_exist_in_keyring", valid_type=str)
        try:
            vault = varvault.from_vault(Keyring, "from-vault", varvault.JsonFilehandler(faulty_existing_vault))
            pytest.fail("Managed to create a vault from a file that should be faulty")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        try:
            vault = varvault.from_vault(Keyring, "from-vault", varvault.JsonFilehandler(faulty_vault_key_missmatch))
            pytest.fail("Managed to create a vault from a file with a key not in keyring, and ignore_keys_not_in_keyring is False")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        vault = varvault.from_vault(Keyring, "from-vault", varvault.JsonFilehandler(faulty_vault_key_missmatch),
                                    varvault.VaultFlags.ignore_keys_not_in_keyring(),
                                    varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        assert this_key_doesnt_exist_in_keyring not in vault, f"Key {this_key_doesnt_exist_in_keyring} was found in the vault when it shouldn't be"

        vault = varvault.from_vault(Keyring, "from-vault", varvault.JsonFilehandler(faulty_vault_key_missmatch),
                                    varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new),
                                    this_key_doesnt_exist_in_keyring=this_key_doesnt_exist_in_keyring)
        assert this_key_doesnt_exist_in_keyring in vault, f"Key {this_key_doesnt_exist_in_keyring} was not found in the vault when it should be added as an extra key"

    def test_insert_type_validation(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        try:
            vault.insert(Keyring.key_valid_type_is_int, "this-should-not-work")
            assert False, "Somehow managed to insert a value for a key that should not work"
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

    def test_clean_return_keys(self):
        vault_new = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))

        @vault_new.vaulter(return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert vault_new.get(Keyring.key_valid_type_is_str) == "valid"

        @vault_new.vaulter(varvault.VaultFlags.clean_return_keys(), return_keys=Keyring.key_valid_type_is_str)
        def _clean():
            return

        _clean()
        assert Keyring.key_valid_type_is_str in vault_new, f"No {Keyring.key_valid_type_is_str} in vault"
        assert vault_new.get(Keyring.key_valid_type_is_str) == "", f"Key {Keyring.key_valid_type_is_str} is not an empty string; {vault_new.get(Keyring.key_valid_type_is_str)}"

    def test_extra_keys(self):
        extra_key1 = varvault.Key("extra_key1", valid_type=dict)
        vault_new = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new), extra_key1=varvault.Key("extra_key1", valid_type=dict))

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

        @vault_new.vaulter(varvault.VaultFlags.clean_return_keys(), return_keys=extra_key1)
        def _clean():
            return
        _clean()

        assert vault_new.get(extra_key1) == {}

    def test_return_tuple_is_single_item(self):
        tuple_item = varvault.Key("tuple_item", valid_type=tuple)
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new), tuple_item=tuple_item)

        @vault.vaulter(varvault.VaultFlags.return_tuple_is_single_item(), return_keys=tuple_item)
        def _set():
            return 1, 2, 3
        _set()

        assert tuple_item in vault, f"Flag: No {tuple_item} found in vault"
        assert vault.get(tuple_item) == (1, 2, 3), "Flag: missmatch"

        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new), tuple_item=tuple_item)

        @vault.vaulter(return_keys=tuple_item)
        def _set():
            return 1, 2, 3
        _set()

        assert tuple_item in vault, f"No flag: No {tuple_item} found in vault"
        assert vault.get(tuple_item) == (1, 2, 3), "No flag: Missmatch"

    def test_split_return_keys(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))
        vault_secondary = varvault.create_vault(Keyring, "vault-secondary", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new_secondary))

        @vault.vaulter(varvault.VaultFlags.split_return_keys(), return_keys=Keyring.key_valid_type_is_str)
        @vault_secondary.vaulter(varvault.VaultFlags.split_return_keys(), return_keys=Keyring.key_valid_type_is_int)
        def _set():
            return varvault.MiniVault({Keyring.key_valid_type_is_str: "valid", Keyring.key_valid_type_is_int: 1})
        _set()

        assert Keyring.key_valid_type_is_str in vault and Keyring.key_valid_type_is_int not in vault
        assert Keyring.key_valid_type_is_int in vault_secondary and Keyring.key_valid_type_is_str not in vault_secondary

        assert vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert vault_secondary.get(Keyring.key_valid_type_is_int) == 1

    def test_return_key_can_be_missing(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))

        @vault.vaulter(return_keys=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def _set_failed():
            return "valid"

        try:
            # Should fail saying that number of returned items do not match the number of keys
            _set_failed()
            pytest.fail("Managed to set a single variable to two keys or something")
        except Exception:
            logger.info("Expected error received; test passed")

        @vault.vaulter(varvault.VaultFlags.return_key_can_be_missing(), return_keys=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def _set_failed_again():
            return "valid"

        try:
            _set_failed_again()
            pytest.fail(f"Managed to set a single variable when {varvault.VaultFlags.return_key_can_be_missing()} is defined; "
                        f"Should have failed saying return var must be of type {varvault.MiniVault}")
        except Exception:
            logger.info("Expected error received; test passed")

        @vault.vaulter(varvault.VaultFlags.return_key_can_be_missing(), return_keys=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def _set_working():
            return varvault.MiniVault({Keyring.key_valid_type_is_str: "valid"})

        _set_working()
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int not in vault
        assert vault.get(Keyring.key_valid_type_is_str) == "valid"

    def test_validate_types_in_minivault_return_values(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))

        @vault.vaulter(return_keys=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def _set_failed():
            return varvault.MiniVault({Keyring.key_valid_type_is_str: 1, Keyring.key_valid_type_is_int: "invalid"})
        try:
            _set_failed()
            pytest.fail("Managed to set invalid values to the vault by returning them in a minivault.")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

    def test_validator_decorator(self):
        try:
            @varvault.validator(function_asserts=True, function_returns_bool=True)
            def invalid_decorator_use(value):
                pass
            pytest.fail("Managed to register a validator function that should not be possible to register. Both 'function_asserts' and 'function_returns_bool' should not be possible to set at the same time")
        except SyntaxError as e:
            logger.info(f"Expected error received; test passed: {e}")

        try:
            @varvault.validator()
            def invalid_decorator_use(value, this_arg_must_not_exist):
                pass
            pytest.fail("Managed to register a validator function that should not be possible to register. Managed to register a validator function with more than 1 positional arg called 'keyvalue'")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        try:
            @varvault.validator(function_asserts=True)
            def invalid_decorator_use(value):
                pass
            pytest.fail("Managed to register a validator function that should not be possible to register. The function needs to contain a call 'assert' in the source if 'function_asserts' is set to True")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        try:
            @varvault.validator(function_returns_bool=True)
            def invalid_decorator_use(value) -> bool:
                pass
            pytest.fail("Managed to register a validator function that should not be possible to register. The function needs to return something in the source if 'function_returns_bool' is set to True")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        @varvault.validator(function_asserts=True, skip_source_assertions=True)
        def valid_decorator_use_1(value):
            pass

        @varvault.validator(function_returns_bool=True, skip_source_assertions=True)
        def valid_decorator_use_2(value) -> bool:
            pass

    def test_key_validation_function(self):
        # This will validate the function and assign some attributes to it that varvault will use when validating the value for the key
        @varvault.validator(function_returns_bool=True)
        def must_be_even(value: int) -> bool:
            return (value % 2) == 0

        @varvault.validator(function_asserts=True)
        def cannot_be_negative(value: int):
            assert value >= 0

        @varvault.validator()
        def no_dashes(value: str):
            assert "-" not in value

        class KeyringKeyValidationFunction(varvault.Keyring):
            int_must_be_even_number = varvault.Key("int_must_be_even_number", valid_type=int, validators=(must_be_even, cannot_be_negative))
            no_dashes_in_str = varvault.Key("no_dashes_in_str", valid_type=str, validators=no_dashes)

        vault = varvault.create_vault(KeyringKeyValidationFunction, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))

        try:
            vault.insert(KeyringKeyValidationFunction.int_must_be_even_number, 1)
            pytest.fail(f"Managed to set {KeyringKeyValidationFunction.int_must_be_even_number} to an uneven number via {vault.insert.__name__}. This should not be possible.")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        @vault.vaulter(return_keys=KeyringKeyValidationFunction.int_must_be_even_number)
        def set_failed():
            return 5
        try:
            set_failed()
            pytest.fail(f"Managed to set {KeyringKeyValidationFunction.int_must_be_even_number} to an uneven number via {vault.vaulter.__name__}. This should not be possible")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        vault.insert(KeyringKeyValidationFunction.int_must_be_even_number, 2)
        assert KeyringKeyValidationFunction.int_must_be_even_number in vault and vault.get(KeyringKeyValidationFunction.int_must_be_even_number) == 2

        @vault.vaulter(varvault.VaultFlags.permit_modifications(), return_keys=KeyringKeyValidationFunction.int_must_be_even_number)
        def set():
            return 4
        set()

        assert KeyringKeyValidationFunction.int_must_be_even_number in vault and vault.get(KeyringKeyValidationFunction.int_must_be_even_number) == 4

    def test_add_minivault_function(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))

        @vault.vaulter(return_keys=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def insert():
            mv = varvault.MiniVault()
            mv.add(Keyring.key_valid_type_is_str, "valid")
            mv.add(Keyring.key_valid_type_is_int, 1)

            return mv

        insert()

        assert Keyring.key_valid_type_is_str in vault and vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert Keyring.key_valid_type_is_int in vault and vault.get(Keyring.key_valid_type_is_int) == 1

    def test_create_vault_file_in_non_existent_dir(self):
        temp_dir = f"{DIR}/temp-dir"
        vault_file = f"{temp_dir}/vault.json"

        try:
            os.remove(vault_file)
            os.removedirs(temp_dir)
        except:
            pass
        assert not os.path.exists(temp_dir), f"Dir {temp_dir} already exists. It's supposed to not exist before we create the vault to make sure varvault creates the required directories"
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(f"{temp_dir}/vault.json"))
        vault.insert(Keyring.key_valid_type_is_str, "valid")
        vault.insert(Keyring.key_valid_type_is_int, 1)
        data = json.load(open(vault_file))
        assert Keyring.key_valid_type_is_str in data and Keyring.key_valid_type_is_int in data

    def test_get_with_default(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))

        vault.insert(Keyring.key_valid_type_is_str, "valid")
        assert Keyring.key_valid_type_is_int not in vault
        try:
            v = vault.get(Keyring.key_valid_type_is_int, default=1)
            pytest.fail(f"Managed to get value from vault with default set, without configuring {varvault.VaultFlags.input_key_can_be_missing()}: {v}")
        except Exception as e:
            pass

        v = vault.get(Keyring.key_valid_type_is_int, varvault.VaultFlags.input_key_can_be_missing())
        assert v is None

        v = vault.get(Keyring.key_valid_type_is_int, varvault.VaultFlags.input_key_can_be_missing(), default=1)
        assert v == 1

        v = vault.get(Keyring.key_valid_type_is_int, varvault.VaultFlags.input_key_can_be_missing()) or 2
        assert v == 2

    def test_get_multiple_with_input_key_can_be_missing_flag(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=varvault.JsonFilehandler(vault_file_new))

        vault.insert(Keyring.key_valid_type_is_str, "valid")

        assert Keyring.key_valid_type_is_int not in vault

        @vault.vaulter(input_keys=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def noflag(**kwargs):
            pass

        try:
            noflag()
            pytest.fail(f"We managed to get this far, which shouldn't be possible: {vault}")
        except:
            pass

        @vault.vaulter(varvault.VaultFlags.input_key_can_be_missing(), input_keys=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def withflag(key_valid_type_is_str: str = None, key_valid_type_is_int: int = None):
            key_valid_type_is_int = key_valid_type_is_int or 1
            assert key_valid_type_is_str == "valid"
            assert key_valid_type_is_int == 1, f"'key_valid_type_is_int' was not {None} when it came into the function: {key_valid_type_is_int}"

        withflag()

    def test_filehandler_exists(self):
        dir = "~/.varvault-test-dir"
        dir_expanded = os.path.expanduser(dir)
        file = "~/.varvault-test-dir/vault.json"
        file_expanded = os.path.expanduser(file)
        try:
            assert not os.path.exists(file_expanded), f"File {file_expanded} already exists, which means it may contain something that should not be overwritten."
            os.makedirs(dir_expanded)
            with open(file_expanded, "w") as f:
                f.write("{}")
            os.environ["DIR"] = "~/.varvault-test-dir"
            os.environ["VAULT_FILE"] = "vault.json"

            fh = varvault.JsonFilehandler("$DIR/$VAULT_FILE")
            assert fh.exists()
        finally:
            try:
                os.remove(file_expanded)
            except OSError:
                pass
            try:
                os.removedirs(dir_expanded)
            except OSError:
                pass

        assert not os.path.exists(file_expanded), f"The file {file_expanded} still exists and it shouldn't. You may want to delete it manually"
        assert not os.path.exists(dir_expanded), f"The directory {dir_expanded} still exists and it shouldn't. You may want to delete it manually"
        logger.info("Done")


