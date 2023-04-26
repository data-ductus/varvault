import json
import os.path
import re
from typing import Callable

import pytest
import tempfile

from _pytest.recwarn import warns

from commons import *

vault_file_new = f"{DIR}/new-vault.json"
vault_file_new_secondary = f"{DIR}/new-vault-secondary.json"
existing_vault = f"{DIR}/existing-vault.json"
faulty_existing_vault = f"{DIR}/faulty-existing-vault.json"
faulty_vault_key_missmatch = f"{DIR}/faulty-vault-key-missmatch.json"


class TestVault:

    @classmethod
    def setup_class(cls):
        tempfile.tempdir = "/tmp" if sys.platform == "darwin" or sys.platform == "linux" else tempfile.gettempdir()

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
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault.manual(output=Keyring.key_valid_type_is_str)
        def _set_valid():
            return "valid-key"

        _set_valid()
        assert vault.get(Keyring.key_valid_type_is_str) == "valid-key"

        @vault.manual(output=Keyring.key_valid_type_is_int)
        def _set_invalid():
            return "invalid-key; must be int"

        try:
            _set_invalid()
            pytest.fail(f"Somehow managed to set an invalid value to key {Keyring.key_valid_type_is_int} (valid type: {Keyring.key_valid_type_is_int.valid_type})")
        except Exception as e:
            assert "Key 'key_valid_type_is_int' requires type to be '<class 'int'>'" in str(e), f"Unexpected error: {e}"
            logger.info(f"Expected error received; test passed")
            assert Keyring.key_valid_type_is_int not in vault

    def test_no_keys(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        called = False
        vault.manual()

        def _set_valid():
            nonlocal called
            called = True
            return "valid-key"

        _set_valid()
        assert called



    def test_put(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        mv = varvault.MiniVault({Keyring.key_valid_type_is_str: "value", Keyring.key_valid_type_is_int: 1})
        vault._put(mv)
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int in vault

        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        vault._put(Keyring.key_valid_type_is_str, "value")
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int not in vault

    def test_create_create_vault(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(existing_vault, mode="r"))
        logger.info(vault)
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int in vault
        assert vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert vault.get(Keyring.key_valid_type_is_int) == 1
        d = json.load(open(existing_vault))
        assert Keyring.key_valid_type_is_str in d and Keyring.key_valid_type_is_int in d, "It appears that loading from the vault file has cleared the vault file unintentionally. This is very bad"

    def test_load_from_one_write_to_another(self):
        existing = varvault.JsonResource(existing_vault, "r").create_mv(**Keyring.get_keys())
        logger.info(f"Existing vault: {existing}")
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        vault.insert_minivault(existing)

        @vault.manual(varvault.Flags.permit_modifications, input=Keyring.key_valid_type_is_str, output=Keyring.key_valid_type_is_str)
        def mod(**kwargs):
            key_valid_type_is_str = kwargs.get(Keyring.key_valid_type_is_str)
            assert key_valid_type_is_str == "valid"
            modded = f"modded"
            return modded
        mod()

        assert vault.get(Keyring.key_valid_type_is_str) == "modded"
        assert json.load(open(vault_file_new)).get(Keyring.key_valid_type_is_str) == "modded", f"The value for {Keyring.key_valid_type_is_str} in vault_filename_to is not the expected"
        assert json.load(open(existing_vault)).get(Keyring.key_valid_type_is_str) == "valid", f"The value for {Keyring.key_valid_type_is_str} in vault_filename_from has changed. This is very bad"

    def test_create_create_vault_no_valid_type_in_key(self):
        class KeyringTemp(varvault.Keyring):
            key_valid_type_is_str = varvault.Key("key_valid_type_is_str")
            key_valid_type_is_int = varvault.Key("key_valid_type_is_int")

        vault = varvault.create(keyring=KeyringTemp, resource=varvault.JsonResource(existing_vault, mode="r"))

    def test_permit_modifications(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        vault.insert(Keyring.key_valid_type_is_str, "valid")
        try:
            @vault.manual(output=Keyring.key_valid_type_is_str)
            def _set():
                return "new-value-that-should-not-go-in"
            _set()

            pytest.fail("Managed to set a new value to an existing key while modifications are not permitted")
        except Exception as e:
            logger.info(f"Expected error received; test passed")
            assert vault.get(Keyring.key_valid_type_is_str) == "valid", f"Value for {Keyring.key_valid_type_is_str} is not what it should be"

        @vault.manual(varvault.Flags.permit_modifications, output=Keyring.key_valid_type_is_str)
        def _set():
            return "new-modified-value"
        _set()

        assert vault.get(Keyring.key_valid_type_is_str) == "new-modified-value", f"Value for {Keyring.key_valid_type_is_str} is not what it should be"

        new_vault = varvault.create(varvault.Flags.permit_modifications, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @new_vault.manual(output=Keyring.key_valid_type_is_str)
        def _set():
            return "new-modified-value-gen-2"
        _set()

        assert new_vault.get(Keyring.key_valid_type_is_str) == "new-modified-value-gen-2", f"Value for {Keyring.key_valid_type_is_str} is not what it should be"

    def test_create_readonly_vault(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(existing_vault, mode="r"))
        try:
            vault.insert(Keyring.key_valid_type_is_int, 1)
            pytest.fail("Insert: Somehow managed to insert a value into a vault that is supposed to be read-only")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

        try:
            @vault.manual(output=Keyring.key_valid_type_is_int)
            def _set():
                return 1
            _set()

            pytest.fail("Vaulter: Somehow managed to insert a value into a vault that is supposed to be read-only")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

    def test_read_only_key_not_in_keyring(self):
        with warns(UserWarning, match=".*is not defined in the keyring.*"):
            json.dump({Keyring.key_valid_type_is_str: "valid", Keyring.key_valid_type_is_int: 1, "temp": "this-should-not-be-in-the-vault"}, open(vault_file_new, "w"))
            vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="r"))
            assert varvault.Key("temp") not in vault, "Vault contains a key that should not be in the vault since it doesn't exist in the keyring"
            assert Keyring.key_valid_type_is_str in vault
            assert Keyring.key_valid_type_is_int in vault

    def test_insert_nonexistent_key(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        temp_key = varvault.Key("temp_key")
        try:
            vault.insert(temp_key, "this-should-not-go-in")
            pytest.fail("Somehow managed to insert a non-existent key into a vault that should not permit this")
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

    # @pytest.mark.filterwarnings("ignore:.*Keys were found in the resource.*", "ignore:.*is not defined in the keyring.*")
    def test_create_from_faulty_vault(self):
        with warns(UserWarning, match=".*is not defined in the keyring.*|.*Keys were found in the resource.*"):
            this_key_doesnt_exist_in_keyring = varvault.Key("this_key_doesnt_exist_in_keyring", valid_type=str)
            try:
                vault = varvault.create(keyring=Keyring, logger=logger,
                                        resource=varvault.JsonResource(faulty_existing_vault, mode="r"))
                pytest.fail("Managed to create a vault from a file that should be faulty")
            except Exception as e:
                logger.info(f"Expected error received; test passed: {e}")

            try:
                vault = varvault.create(keyring=Keyring,
                                        logger=logger,
                                        resource=varvault.JsonResource(faulty_vault_key_missmatch, mode="a"))
                pytest.fail("Managed to create a vault from a file with a key not in keyring, and ignore_keys_not_in_keyring is False and the resource is not read-only (it's in append mode)")
            except Exception as e:
                logger.info(f"Expected error received; test passed: {e}")

            vault = varvault.create(varvault.Flags.ignore_keys_not_in_keyring, keyring=Keyring, name="from-vault",
                                    logger=logger,
                                    resource=varvault.JsonResource(faulty_vault_key_missmatch, mode="r"))
            assert this_key_doesnt_exist_in_keyring not in vault, f"Key {this_key_doesnt_exist_in_keyring} was found in the vault when it shouldn't be"

            vault = varvault.create(keyring=Keyring,
                                    resource=varvault.JsonResource(faulty_vault_key_missmatch, mode="r"),
                                    logger=logger,
                                    this_key_doesnt_exist_in_keyring=this_key_doesnt_exist_in_keyring)
            assert this_key_doesnt_exist_in_keyring in vault, f"Key {this_key_doesnt_exist_in_keyring} was not found in the vault when it should be added as an extra key"

    def test_insert_type_validation(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        try:
            vault.insert(Keyring.key_valid_type_is_int, "this-should-not-work")
            assert False, "Somehow managed to insert a value for a key that should not work"
        except Exception as e:
            logger.info(f"Expected error received; test passed: {e}")

    def test_clean_output_keys(self):
        vault_new = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault_new.manual(output=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert vault_new.get(Keyring.key_valid_type_is_str) == "valid"

        @vault_new.manual(varvault.Flags.clean_output_keys, output=Keyring.key_valid_type_is_str)
        def _clean():
            return

        _clean()
        assert Keyring.key_valid_type_is_str in vault_new, f"No {Keyring.key_valid_type_is_str} in vault"
        assert vault_new.get(Keyring.key_valid_type_is_str) == "", f"Key {Keyring.key_valid_type_is_str} is not an empty string; {vault_new.get(Keyring.key_valid_type_is_str)}"

    def test_extra_keys(self):
        extra_key1 = varvault.Key("extra_key1", valid_type=dict)
        vault_new = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"), extra_key1=varvault.Key("extra_key1", valid_type=dict))

        @vault_new.manual(output=extra_key1)
        def _set_invalid():
            return [1, 2, 3]
        try:
            _set_invalid()
            pytest.fail("Unexpectedly managed to set an invalid value to an extra key")
        except Exception as e:
            assert "Key 'extra_key1' requires type to be '<class 'dict'>'" in str(e), f"Unexpected error message: {e}"
            logger.info(f"Expected error received; test passed: {e}")

        @vault_new.manual(output=extra_key1)
        def _set_valid():
            return {"a": 1, "b": 2, "c": 3}
        _set_valid()

        @vault_new.manual(varvault.Flags.clean_output_keys, output=extra_key1)
        def _clean():
            return
        _clean()

        assert vault_new.get(extra_key1) == {}

    def test_return_tuple_is_single_item(self):
        tuple_item = varvault.Key("tuple_item", valid_type=tuple)
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"), tuple_item=tuple_item)

        @vault.manual(varvault.Flags.return_tuple_is_single_item, output=tuple_item)
        def _set():
            return 1, 2, 3
        _set()

        assert tuple_item in vault, f"Flag: No {tuple_item} found in vault"
        assert vault.get(tuple_item) == (1, 2, 3), "Flag: missmatch"

        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"), tuple_item=tuple_item)

        @vault.manual(output=tuple_item)
        def _set():
            return 1, 2, 3
        _set()

        assert tuple_item in vault, f"No flag: No {tuple_item} found in vault"
        assert vault.get(tuple_item) == (1, 2, 3), "No flag: Missmatch"

    def test_split_output_keys(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        vault_secondary = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new_secondary, mode="w"))

        @vault.manual(varvault.Flags.split_output_keys, output=Keyring.key_valid_type_is_str)
        @vault_secondary.manual(varvault.Flags.split_output_keys, output=Keyring.key_valid_type_is_int)
        def _set():
            return varvault.MiniVault({Keyring.key_valid_type_is_str: "valid", Keyring.key_valid_type_is_int: 1})
        _set()

        assert Keyring.key_valid_type_is_str in vault and Keyring.key_valid_type_is_int not in vault
        assert Keyring.key_valid_type_is_int in vault_secondary and Keyring.key_valid_type_is_str not in vault_secondary

        assert vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert vault_secondary.get(Keyring.key_valid_type_is_int) == 1

    def test_return_key_can_be_missing(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault.manual(output=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def _set_failed():
            return "valid"

        try:
            # Should fail saying that number of returned items do not match the number of keys
            _set_failed()
            pytest.fail("Managed to set a single variable to two keys or something")
        except Exception:
            logger.info("Expected error received; test passed")

        @vault.manual(varvault.Flags.output_key_can_be_missing, output=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def _set_failed_again():
            return "valid"

        try:
            _set_failed_again()
            pytest.fail(f"Managed to set a single variable when {varvault.Flags.output_key_can_be_missing} is defined; "
                        f"Should have failed saying return var must be of type {varvault.MiniVault}")
        except Exception:
            logger.info("Expected error received; test passed")

        @vault.manual(varvault.Flags.output_key_can_be_missing, output=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def _set_working():
            return varvault.MiniVault({Keyring.key_valid_type_is_str: "valid"})

        _set_working()
        assert Keyring.key_valid_type_is_str in vault
        assert Keyring.key_valid_type_is_int not in vault
        assert vault.get(Keyring.key_valid_type_is_str) == "valid"

    def test_validate_types_in_minivault_return_values(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault.manual(output=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
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

        with warns(SyntaxWarning, match="If you define the validator-function to say that it returns a bool"):
            @varvault.validator(function_returns_bool=True)
            def returns_no_bool(value) -> int:
                return 1

        @varvault.validator(function_asserts=True)
        def cannot_be_negative(value: int):
            assert value >= 0, "Value cannot be negative"

        @varvault.validator()
        def no_dashes(value: str):
            assert "-" not in value

        class KeyringKeyValidationFunction(varvault.Keyring):
            int_must_be_even_number = varvault.Key("int_must_be_even_number", valid_type=int, validators=must_be_even)
            int_cannot_be_negative = varvault.Key("int_cannot_be_negative", valid_type=int, validators=cannot_be_negative)
            validator_returns_no_bool = varvault.Key("validator_returns_no_bool", valid_type=int, validators=returns_no_bool)
            no_dashes_in_str = varvault.Key("no_dashes_in_str", valid_type=str, validators=no_dashes)

        vault = varvault.create(keyring=KeyringKeyValidationFunction, resource=varvault.JsonResource(vault_file_new, mode="w"))

        with pytest.raises(varvault.ValidatorException) as e:
            vault.insert(KeyringKeyValidationFunction.int_must_be_even_number, 1)
        assert "must_be_even" in str(e.value)

        @vault.manual(output=KeyringKeyValidationFunction.int_must_be_even_number)
        def set_failed():
            return 5
        with pytest.raises(varvault.ValidatorException) as e:
            set_failed()
        assert "must_be_even" in str(e.value)

        with pytest.raises(varvault.ValidatorException) as e:
            vault.insert(KeyringKeyValidationFunction.int_cannot_be_negative, -2)
        assert "Value cannot be negative" in str(e.value)

        vault.insert(KeyringKeyValidationFunction.int_must_be_even_number, 2)
        assert KeyringKeyValidationFunction.int_must_be_even_number in vault and vault.get(KeyringKeyValidationFunction.int_must_be_even_number) == 2

        with pytest.raises(varvault.ValidatorException) as e:
            vault.insert(KeyringKeyValidationFunction.validator_returns_no_bool, 1)
        assert "The return value is of type" in str(e.value)

        @vault.manual(varvault.Flags.permit_modifications, output=KeyringKeyValidationFunction.int_must_be_even_number)
        def set():
            return 4
        set()

        assert KeyringKeyValidationFunction.int_must_be_even_number in vault and vault.get(KeyringKeyValidationFunction.int_must_be_even_number) == 4

    def test_key_validation_error_message(self):
        @varvault.validator(function_asserts=True)
        def must_be_above_zero(value: int):
            assert value >= 0

        class KeyringTemp(varvault.Keyring):
            int_must_be_above_zero = varvault.Key("int_must_be_above_zero", valid_type=int, validators=must_be_above_zero)

        vault = varvault.create(keyring=KeyringTemp, name="vault")
        try:
            vault.insert(KeyringTemp.int_must_be_above_zero, -1)
            pytest.fail(f"Managed to set {KeyringTemp.int_must_be_above_zero} to a negative number via {vault.insert.__name__}. This should not be possible.")
        except Exception as e:
            assert KeyringTemp.int_must_be_above_zero in str(e), f"Expected the key {KeyringTemp.int_must_be_above_zero} to be mentioned in the error message, but it was not. Error message: {e}"
            logger.info(e)

    def test_add_minivault_function(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault.manual(output=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
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
        except OSError:
            pass
        try:
            os.removedirs(temp_dir)
        except OSError:
            pass
        assert not os.path.exists(temp_dir), f"Dir {temp_dir} already exists. It's supposed to not exist before we create the vault to make sure varvault creates the required directories"
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(f"{temp_dir}/vault.json", mode="w"))
        vault.insert(Keyring.key_valid_type_is_str, "valid")
        vault.insert(Keyring.key_valid_type_is_int, 1)
        data = json.load(open(vault_file))
        assert Keyring.key_valid_type_is_str in data and Keyring.key_valid_type_is_int in data

    def test_get_with_default(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))

        vault.insert(Keyring.key_valid_type_is_str, "valid")
        assert Keyring.key_valid_type_is_int not in vault
        try:
            v = vault.get(Keyring.key_valid_type_is_int, default=1)
            pytest.fail(f"Managed to get value from vault with default set, without configuring {varvault.Flags.input_key_can_be_missing}: {v}")
        except Exception as e:
            pass

        v = vault.get(Keyring.key_valid_type_is_int, varvault.Flags.input_key_can_be_missing)
        assert v is None

        v = vault.get(Keyring.key_valid_type_is_int, varvault.Flags.input_key_can_be_missing, default=1)
        assert v == 1

        v = vault.get(Keyring.key_valid_type_is_int, varvault.Flags.input_key_can_be_missing) or 2
        assert v == 2

    def test_get_multiple_with_input_key_can_be_missing_flag(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))

        vault.insert(Keyring.key_valid_type_is_str, "valid")

        assert Keyring.key_valid_type_is_int not in vault

        @vault.manual(input=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def noflag(**kwargs):
            pass

        try:
            noflag()
            pytest.fail(f"We managed to get this far, which shouldn't be possible: {vault}")
        except:
            pass

        @vault.manual(varvault.Flags.input_key_can_be_missing, input=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
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

            fh = varvault.JsonResource("$DIR/$VAULT_FILE")
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

    def test_create_vault_produces_valid_json(self):
        assert not os.path.exists(vault_file_new)
        # Creating a vault from scratch should produce a valid but empty JSON file
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        assert json.load(open(vault_file_new)) == {}

    def test_input_keys_as_kw_vars_only(self):
        vault = varvault.create(varvault.Flags.use_signature_for_input_keys, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))

        vault.insert(Keyring.key_valid_type_is_str, "valid")
        vault.insert(Keyring.key_valid_type_is_int, 1)

        @vault.manual()
        def fn_pure_kw_only(*, key_valid_type_is_str=varvault.AssignedByVault, key_valid_type_is_int=varvault.AssignedByVault):
            assert key_valid_type_is_str == "valid"
            assert key_valid_type_is_int == 1

        fn_pure_kw_only()

        @vault.manual()
        def fn_pure_kw_or_positional(key_valid_type_is_str=varvault.AssignedByVault, key_valid_type_is_int=varvault.AssignedByVault):
            assert key_valid_type_is_str == "valid"
            assert key_valid_type_is_int == 1

        fn_pure_kw_or_positional()

        @vault.manual(input=Keyring.key_valid_type_is_str)
        def fn_mixed(key_valid_type_is_str=varvault.AssignedByVault, key_valid_type_is_int=varvault.AssignedByVault):
            assert key_valid_type_is_str == "valid"
            assert key_valid_type_is_int == 1

        fn_mixed()

        @vault.manual()
        def fn_pure_with_args(a1, key_valid_type_is_str=varvault.AssignedByVault, key_valid_type_is_int=varvault.AssignedByVault):
            assert a1 == 3.14
            assert key_valid_type_is_str == "valid"
            assert key_valid_type_is_int == 1

        fn_pure_with_args(3.14)

        @vault.manual(input=Keyring.key_valid_type_is_str)
        def fn_mixed_with_args(a1, key_valid_type_is_str=varvault.AssignedByVault, key_valid_type_is_int=varvault.AssignedByVault):
            assert a1 == 3.14
            assert key_valid_type_is_str == "valid"
            assert key_valid_type_is_int == 1

        fn_mixed_with_args(3.14)

        try:
            @vault.manual()
            def fn_with_typo(key_valid_type_is_string=varvault.AssignedByVault, key_valid_type_is_integer=varvault.AssignedByVault):  # Note the typos in the key names
                assert key_valid_type_is_string is None
                assert key_valid_type_is_integer is None
            pytest.fail("We managed to get this far, which shouldn't be possible")
        except AssertionError:
            pass

        try:
            @vault.manual()
            def fn_faulty_default_assignment(key_valid_type_is_str=None, key_valid_type_is_int=None):
                assert key_valid_type_is_str == "valid"
                assert key_valid_type_is_int == 1
            pytest.fail("We managed to get this far, which shouldn't be possible")
        except AssertionError as e:
            pass

        try:
            @vault.manual()
            def fn_mixed_faulty_default_assignment(key_valid_type_is_str=None, key_valid_type_is_integer=varvault.AssignedByVault):
                assert key_valid_type_is_str == "valid"
                assert key_valid_type_is_integer == 1
            pytest.fail("We managed to get this far, which shouldn't be possible")
        except AssertionError as e:
            pass

    def test_create_vault_no_resource(self):
        vault = varvault.create(keyring=Keyring, name="vault")
        assert vault.resource is None
        vault.insert(Keyring.key_valid_type_is_str, "valid")
        vault.insert(Keyring.key_valid_type_is_int, 1)
        assert vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert vault.get(Keyring.key_valid_type_is_int) == 1

    def test_create_vault_with_json_resource_relative_path(self):
        try:
            vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(os.path.basename(vault_file_new), mode="w"))
            assert vault.resource
            assert vault.resource.path == os.path.basename(vault_file_new)
        finally:
            os.remove(os.path.basename(vault_file_new))

    def test_key_usages(self):
        class KeyringTemporary(varvault.Keyring):
            k1 = varvault.Key("k1")
            k2 = varvault.Key("k2")
            k3 = varvault.Key("k3")
        vault = varvault.create(keyring=KeyringTemporary, name="vault")
        @vault.manual(output=(KeyringTemporary.k1, KeyringTemporary.k2, KeyringTemporary.k3))
        def _set():
            return 1, "valid", 3.14

        try:
            vault.get(KeyringTemporary.k1)
            pytest.fail("We managed to get this far, which shouldn't be possible")
        except KeyError as e:
            logger.info(e.args[0])
            assert "test_vault._set" in e.args[0]

        _set()

        @vault.manual(input=(KeyringTemporary.k1, KeyringTemporary.k2))
        def _use_first(k1=varvault.AssignedByVault, k2=varvault.AssignedByVault):
            assert k1 == 1
            assert k2 == "valid"

        _use_first()

        @vault.manual(input=KeyringTemporary.k3)
        def _use_second(k3=varvault.AssignedByVault):
            assert k3 == 3.14

        _use_second()

        @vault.manual(varvault.Flags.permit_modifications, input=KeyringTemporary.k3, output=KeyringTemporary.k3)
        def _override(k3):
            assert k3 == 3.14
            return k3 * 2
        _override()

        assert vault.get(KeyringTemporary.k3) == 6.28
        assert KeyringTemporary.k1.usages.as_input == ['test_vault._use_first']
        assert KeyringTemporary.k2.usages.as_input == ['test_vault._use_first']
        assert KeyringTemporary.k3.usages.as_input == ['test_vault._override', 'test_vault._use_second']
        assert KeyringTemporary.k1.usages.as_return == ['test_vault._set']
        assert KeyringTemporary.k2.usages.as_return == ['test_vault._set']
        assert KeyringTemporary.k3.usages.as_return == ['test_vault._override', 'test_vault._set']

    def test_signature_with_missing_input_keys(self):
        vault = varvault.create(varvault.Flags.use_signature_for_input_keys,
                                keyring=Keyring,
                                name="vault",
                                resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault.manual(varvault.Flags.input_key_can_be_missing, input=Keyring.key_valid_type_is_str)
        def _use(key_valid_type_is_str=varvault.AssignedByVault):
            assert not key_valid_type_is_str
            assert key_valid_type_is_str is None, f"It's {type(key_valid_type_is_str)}, not {None}, which is what it should be"

        _use()

    def test_load_from_backup(self):
        assert not os.path.exists(vault_file_new)
        json.dump({Keyring.key_valid_type_is_str: "valid", Keyring.key_valid_type_is_int: 1}, open(f"{vault_file_new}.bak", "w"))
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="a"))

        assert vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert vault.get(Keyring.key_valid_type_is_int) == 1

        assert not os.path.exists(f"{vault_file_new}.bak"), "This file should have been renamed to remove extension '.bak'"

    def test_lambdas(self):
        vault = varvault.create(keyring=Keyring, name="vault")

        # Define the lambda function that will be used to set the value of the key
        setter: Callable = vault.lambdavaulter(lambda: 1, output_keys=Keyring.key_valid_type_is_int)
        assert callable(setter)

        # Define the lambda function that will be used to get the value of the key. Note that the name of the input variable is identical to the name of the key.
        getter: Callable = vault.lambdavaulter(lambda key_valid_type_is_int: key_valid_type_is_int * 3, input_keys=Keyring.key_valid_type_is_int)
        assert callable(getter)

        # Set the value of the key using the lambda
        setter()

        # Assert that the value of the key is as expected after setting with the lambda
        assert vault.get(Keyring.key_valid_type_is_int) == 1

        # Use the getter-lambda to get the value from the vault and assert that it is as expected
        assert getter() == 3

    def test_verify_faulty_extra_keys(self):
        try:
            vault = varvault.create(keyring=Keyring, name="vault", ex_1="ex_1", ex_2="ex_2")
            pytest.fail("We managed to get this far, which shouldn't be possible")
        except ValueError as e:
            assert "Faulty keys that must be changed: ['ex_1', 'ex_2']" in str(e.args[0]), e
        k1 = varvault.Key("ex1", valid_type=float)
        k2 = varvault.Key("ex2", valid_type=list)
        vault = varvault.create(keyring=Keyring, name="vault", k1=k1, k2=k2)
        vault.insert(k1, 3.14)
        vault.insert(k2, ["valid", "list", "of", "strings"])
        assert vault.get(k1) == 3.14
        assert vault.get(k2) == ["valid", "list", "of", "strings"]

    def test_modifiers(self):

        @varvault.modifier()
        def modifier_expand_path(value: str):
            return os.path.expanduser(value)

        @varvault.modifier()
        def modifier_multiply(value: int or float):
            return value * 2

        @varvault.modifier()
        def modifier_add(value: int or float):
            return value + 2

        @varvault.modifier()
        def modifier_failed(value: int or float):
            if value < 0:
                raise ValueError(f"Value {value} is less than 0")
            return value * 2
        try:
            @varvault.modifier()
            def modifier_no_return(value: int or float):
                value = value + 2
        except AssertionError as e:
            assert "No return-statement found in the functions source" in str(e.args[0]), e

        class KeyringModifiers(varvault.Keyring):
            key_path = varvault.Key("key_path", valid_type=str, modifiers=modifier_expand_path)
            key_int = varvault.Key("key_int", valid_type=int, modifiers=modifier_multiply)
            key_float = varvault.Key("key_float", valid_type=float, modifiers=(modifier_add, modifier_multiply))
            key_failed = varvault.Key("key_failed", valid_type=float, modifiers=modifier_failed)

        vault = varvault.create(keyring=KeyringModifiers, name="vault")
        vault.insert(KeyringModifiers.key_path, "~/.varvault")
        expected = os.path.expanduser("~/.varvault")
        assert vault.get(KeyringModifiers.key_path) == expected

        vault.insert(KeyringModifiers.key_int, 1)
        assert vault.get(KeyringModifiers.key_int) == 2, "The modifier should have doubled the value"

        vault.insert(KeyringModifiers.key_float, 1.0)
        assert vault.get(KeyringModifiers.key_float) == 6.0, "The modifiers should have added 2 and then doubled the value to 6.0"

        with pytest.raises(varvault.ModifierException) as e:
            vault.insert(KeyringModifiers.key_failed, -1.0)
        assert "Value -1.0 is less than 0" in str(e.value.args[0]), e

    def test_warning_write_to_read_only_resource(self):
        resource = varvault.JsonResource(vault_file_new, mode="w")
        resource.write({Keyring.key_valid_type_is_int: 1})

        vault = varvault.create(keyring=Keyring, name="vault", resource=varvault.JsonResource(vault_file_new, mode="r"))
        with warns(UserWarning, match="It appears you are trying to write to a resource that is not permitted to write to and the vault has already been initialized"):
            vault.insert(Keyring.key_valid_type_is_str, "should not be written")

        resource = varvault.JsonResource(vault_file_new, mode="r")
        assert Keyring.key_valid_type_is_str not in resource.create_mv(**Keyring.get_keys()), "The key should not have been written to the file"

        with warns(UserWarning, match="Tried to write to a resource defined as read-only"):
            resource.write({Keyring.key_valid_type_is_str: "should not be written"})
        assert Keyring.key_valid_type_is_str not in resource.create_mv(**Keyring.get_keys()), "The key should not have been written to the file"

    def test_faulty_put_on_vault(self):
        # For coverage
        vault = varvault.create(keyring=Keyring)
        with pytest.raises(NotImplementedError) as e:
            vault._put({Keyring.key_valid_type_is_str: "valid"})
        assert "Not implemented" in str(e.value.args[0]), e

    def test_vaulted_function_raises_exception(self):
        vault = varvault.create(keyring=Keyring)
        vault.insert(Keyring.key_valid_type_is_str, "valid")

        @vault.manual(input=Keyring.key_valid_type_is_str)
        async def async_func(id, key_valid_type_is_str: str = varvault.AssignedByVault):
            raise ValueError(key_valid_type_is_str)

        with pytest.raises(ValueError) as e:
            varvault.concurrent_execution(async_func, [1])
        assert "valid" in str(e.value.args[0]), e

        @vault.manual(input=Keyring.key_valid_type_is_str)
        def func(key_valid_type_is_str: str = varvault.AssignedByVault):
            raise ValueError(key_valid_type_is_str)

        with pytest.raises(ValueError) as e:
            func()
        assert "valid" in str(e.value.args[0]), e

    def test_no_error_logging_flag(self):
        vault = varvault.create(keyring=Keyring)
        vault.insert(Keyring.key_valid_type_is_str, "valid")

        @vault.manual(varvault.Flags.no_error_logging, input=Keyring.key_valid_type_is_str)
        async def async_func(id, key_valid_type_is_str: str = varvault.AssignedByVault):
            raise ValueError(key_valid_type_is_str)

        with pytest.raises(ValueError) as e:
            varvault.concurrent_execution(async_func, [1])
        assert "valid" in str(e.value.args[0]), e

        @vault.manual(varvault.Flags.no_error_logging, input=Keyring.key_valid_type_is_str)
        def func(key_valid_type_is_str: str = varvault.AssignedByVault):
            raise ValueError(key_valid_type_is_str)

        with pytest.raises(ValueError) as e:
            func()
        assert "valid" in str(e.value.args[0]), e

    def test_flag_is_invalid_type(self):
        vault = varvault.create(keyring=Keyring)
        with pytest.raises(TypeError) as e:
            vault.insert(Keyring.key_valid_type_is_str, "valid", varvault.Flags.permit_modifications.value)
        assert "is not of type" in str(e.value.args[0]), e

        with pytest.raises(TypeError) as e:
            @vault.manual(varvault.Flags.permit_modifications.value, output=Keyring.key_valid_type_is_str)
            def func():
                return "valid"
            func()

        assert "is not of type" in str(e.value.args[0]), e

    def test_return_values_cannot_be_none(self):
        class KeyringTemp:
            key_valid_type_is_str = varvault.Key("key_valid_type_is_str", valid_type=str, can_be_none=True)
        vault = varvault.create(keyring=Keyring)
        with pytest.raises(ValueError) as e:
            @vault.manual(varvault.Flags.return_values_cannot_be_none, output=KeyringTemp.key_valid_type_is_str)
            def func():
                return None
            func()
        assert "The value mapped to key_valid_type_is_str is None and Flags.return_values_cannot_be_none is defined" in str(e.value.args[0]), e

    def test_get(self):
        vault = varvault.create(keyring=Keyring)
        vault.insert(Keyring.key_valid_type_is_str, "valid")
        vault.insert(Keyring.key_valid_type_is_int, 1)

        key_valid_type_is_str = vault.get(Keyring.key_valid_type_is_str)
        assert key_valid_type_is_str == "valid", key_valid_type_is_str

        mv: varvault.MiniVault = vault.get([Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int])
        assert Keyring.key_valid_type_is_str in mv and Keyring.key_valid_type_is_int in mv, mv
        assert mv[Keyring.key_valid_type_is_str] == "valid" and mv[Keyring.key_valid_type_is_int] == 1, mv
        values = mv.values()
        assert "valid" in values and 1 in values, values

        with pytest.raises(NotImplementedError) as e:
            vault.get({Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int})
        assert re.match("Type .* is not supported for the 'get' method", str(e.value.args[0])) is not None, e

    def test_clean_no_valid_type(self):
        class Temp:
            def __init__(self, a1, a2):
                self.a1 = a1
                self.a2 = a2

        class KeyringTemp(varvault.Keyring):
            key_no_valid_type = varvault.Key("key_no_valid_type")
            key_special_valid_type = varvault.Key("key_special_valid_type", valid_type=Temp)

        vault = varvault.create(keyring=KeyringTemp)
        vault.insert(KeyringTemp.key_no_valid_type, "valid")
        vault.insert(KeyringTemp.key_special_valid_type, Temp("a1", "a2"))

        @vault.manual(varvault.Flags.clean_output_keys, output=(KeyringTemp.key_no_valid_type, KeyringTemp.key_special_valid_type))
        def clean():
            return

        clean()
        assert vault.get(KeyringTemp.key_no_valid_type) is None, vault.get(KeyringTemp.key_no_valid_type)
        assert vault.get(KeyringTemp.key_special_valid_type) is None, vault.get(KeyringTemp.key_special_valid_type)

    def test_validator_modifier_undecorated(self):
        def validate(value):
            return value == "valid"

        def modify(value):
            return value + " modified"

        with pytest.raises(ValueError) as e:
            key_validate = varvault.Key("key_validate", valid_type=str, validators=validate)
        assert "is not decorated with <function validator" in str(e.value.args[0]), e

        with pytest.raises(ValueError) as e:
            key_modify = varvault.Key("key_modify", valid_type=str, modifiers=modify)
        assert "is not decorated with <function modifier" in str(e.value.args[0]), e

    def test_compare_key_with_non_str(self):
        key = varvault.Key("key")
        assert not key == 1, key

    def test_valid_type_corner_cases(self):
        class Temp:
            pass

        class KeyringTemp(varvault.Keyring):
            key_is_type_can_be_none = varvault.Key("key_is_type_can_be_none", valid_type=Temp, can_be_none=True)
            key_is_type_cannot_be_none = varvault.Key("key_is_type_cannot_be_none", valid_type=Temp)
            key_valid_type_is_int = varvault.Key("key_valid_type_is_int", valid_type=int)

        vault = varvault.create(varvault.Flags.permit_modifications, keyring=KeyringTemp)
        vault.insert(KeyringTemp.key_is_type_can_be_none, Temp)

        with pytest.raises(ValueError) as e:
            vault.insert(KeyringTemp.key_is_type_can_be_none, dict())
        assert "requires type to be" in str(e.value.args[0]), e
        vault.insert(KeyringTemp.key_is_type_cannot_be_none, Temp)
        assert vault.get(KeyringTemp.key_is_type_cannot_be_none) is Temp, vault.get(KeyringTemp.key_is_type_cannot_be_none)
        assert vault.get(KeyringTemp.key_is_type_can_be_none) is Temp, vault.get(KeyringTemp.key_is_type_can_be_none)

    def test_get_non_matching_key(self):
        class KeyringTemp(varvault.Keyring):
            key_valid_type_is_int = varvault.Key("key_valid_type_is_int", valid_type=int)
        with pytest.raises(KeyError) as e:
            KeyringTemp.get_key_by_matching_string("not_valid")
        assert "Failed to get matching key for string: not_valid" in str(e.value.args[0]), e

    def test_validator_bool_annotate_warning(self):
        with warns(SyntaxWarning) as w:
            @varvault.validator(function_returns_bool=True)
            def validate(value):  # Note lack of annotated bool return type
                return value == "valid"
        assert "If you define the validator-function to say that it returns a bool, you should really also annotate the function to say it returns a bool." in str(w[0].message), w

    def test_try_modify_mode_properties(self):
        resource = varvault.JsonResource(existing_vault, mode=varvault.ResourceModes.READ)
        with pytest.raises(AttributeError) as e:
            resource.mode_properties.load = False  # Piss off, you can't modify mode_properties after they've been created
        assert "ModeProperties are immutable" in str(e.value.args[0]), e

    def test_resource_invalid_mode(self):
        with pytest.raises(ValueError) as e:
            resource = varvault.JsonResource(existing_vault, mode="invalid")
        assert "Invalid mode: invalid" in str(e.value.args[0]), e

    def test_non_existing_resource(self):
        with pytest.raises(varvault.ResourceNotFoundError) as e:
            resource = varvault.JsonResource("non_existing_resource.json")
        assert "Resource not found at:" in str(e.value.args[0]), e

    def test_resource_invalid_value_write(self):
        class Temp:
            pass

        resource = varvault.JsonResource(vault_file_new, mode="w")
        with pytest.raises(varvault.ResourceNotFoundError) as e:
            d = dict(k=Temp)
            assert not resource.writable(d)
            resource.write(d)
        assert "Failed to write to the resource:" in str(e.value.args[0]), e

    def test_resource_invalid_value_read(self):
        resource = varvault.JsonResource(vault_file_new, mode="w")
        resource.create()
        open(vault_file_new, "w").write("invalid")

        try:
            resource.read()
        except varvault.ResourceNotFoundError as e:
            assert "Failed to read from the resource" in str(e), e
        resource = varvault.JsonResource(vault_file_new, mode="r")
        with pytest.raises(varvault.ResourceNotFoundError) as e:
            resource.create()
        assert "Unable to read from resource at" in str(e.value.args[0]), e

    def test_append_resource_mode(self):
        resource = varvault.JsonResource(vault_file_new, mode="a")
        resource.create()
        resource.write({"key": "value"})
        resource = varvault.JsonResource(vault_file_new, mode="r")
        assert resource.read() == {"key": "value"}, resource.read()

    def test_modifier_plus_validator_on_insert(self):
        @varvault.validator(function_returns_bool=True)
        def no_dashes_in_str(value: str) -> bool:
            return re.match(r"^[a-zA-Z0-9_]*$", value) is not None

        @varvault.modifier()
        def remove_dashes_in_str(value: str) -> str:
            return value.replace("-", "_")

        @varvault.modifier()
        def remove_underscore_in_str(value: str) -> str:
            return value.replace("_", "-")

        @varvault.validator(function_returns_bool=True)
        def no_underscore_in_str(value: str) -> bool:
            return re.match(r"^[a-zA-Z0-9-]*$", value) is not None

        class KeyringKeyValidationFunction(varvault.Keyring):
            name = varvault.Key("name", valid_type=str, modifiers=remove_underscore_in_str, validators=no_underscore_in_str)
            path = varvault.Key("path", valid_type=str, modifiers=remove_dashes_in_str, validators=no_dashes_in_str)

        vault = varvault.create(varvault.Flags.permit_modifications, keyring=KeyringKeyValidationFunction)
        vault.insert(KeyringKeyValidationFunction.name, "will_be_modified_to_dashes")
        vault.insert(KeyringKeyValidationFunction.path, "will-be-modified-to-underscores")
        assert vault.get(KeyringKeyValidationFunction.name) == "will-be-modified-to-dashes", vault.get(KeyringKeyValidationFunction.name)
        assert vault.get(KeyringKeyValidationFunction.path) == "will_be_modified_to_underscores", vault.get(KeyringKeyValidationFunction.path)

