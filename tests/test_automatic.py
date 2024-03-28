import tempfile
import time

import pytest

from commons import *

vault_file_new = f"{DIR}/new-vault.json"
vault_file_new_secondary = f"{DIR}/new-vault-secondary.json"
existing_vault = f"{DIR}/existing-vault.json"
faulty_existing_vault = f"{DIR}/faulty-existing-vault.json"
faulty_vault_key_missmatch = f"{DIR}/faulty-vault-key-missmatch.json"


class KeyringAutomatic(varvault.Keyring):
    trigger = varvault.Key("trigger", valid_type=str)
    first = varvault.Key("first", valid_type=str)
    second = varvault.Key("second", valid_type=str)
    third = varvault.Key("third", valid_type=str)
    final = varvault.Key("final", valid_type=str)


class TestAutomatic:

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

    def test_dev(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))

        # Define a automatic that will be triggered when the value for the key 'first' is inserted into the vault
        @vault.automatic(input=KeyringAutomatic.first, output=KeyringAutomatic.second)
        def f(first: str = varvault.AssignedByVault):
            return first + "2"

        # Inserting a value for the key 'first' into the vault will trigger the automatic defined above
        vault.insert(KeyringAutomatic.first, "go")

        # The automatic will be called and the value for the key 'second' will be set
        assert KeyringAutomatic.second in vault

        # The value for the key 'second' should be 'go2'
        assert vault.get(KeyringAutomatic.second) == "go2"

    def test_automatic(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))
        called_first = False
        called_second = False
        called_third = False

        @vault.automatic(input=KeyringAutomatic.first, output=KeyringAutomatic.second)
        def one(first: str = varvault.AssignedByVault):
            nonlocal called_first
            called_first = True
            assert isinstance(first, str)
            return "will trigger second"

        @vault.automatic(input=KeyringAutomatic.second, output=KeyringAutomatic.third)
        def two(second: str = varvault.AssignedByVault):
            nonlocal called_second
            called_second = True
            assert isinstance(second, str)
            return "will trigger third"

        @vault.automatic(input=KeyringAutomatic.third, output=KeyringAutomatic.final)
        def three(third: str = varvault.AssignedByVault):
            nonlocal called_third
            called_third = True
            assert isinstance(third, str)
            return "final"

        @vault.manual(output=KeyringAutomatic.first)
        def start():
            return "first"

        # This will trigger function 'one', which will trigger function 'two', which will trigger function 'three'
        start()

        # All functions should have been called
        assert called_first
        assert called_second
        assert called_third

        # All keys should have been set to the following expected values
        assert vault.get(KeyringAutomatic.first) == "first"
        assert vault.get(KeyringAutomatic.second) == "will trigger second"
        assert vault.get(KeyringAutomatic.third) == "will trigger third"
        assert vault.get(KeyringAutomatic.final) == "final"

    def test_no_keys(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))
        called = False

        @vault.automatic()
        def sub():
            nonlocal called
            called = True

        sub()

        # All functions should have been called
        assert called

    def test_automatic_threaded(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))
        called_first = False
        num_calls_first = 0
        called_second = False
        num_calls_second = 0
        called_third = False
        num_calls_third = 0
        sleep_dur = 2

        @vault.automatic(threaded=True, input=KeyringAutomatic.trigger, output=KeyringAutomatic.first)
        def one(**kwargs):
            logger.info("one")
            nonlocal called_first
            nonlocal num_calls_first
            num_calls_first += 1
            called_first = True
            time.sleep(sleep_dur)
            return "first"

        @vault.automatic(threaded=True, input=KeyringAutomatic.trigger, output=KeyringAutomatic.second)
        def two(**kwargs):
            logger.info("two")
            nonlocal called_second
            nonlocal num_calls_second
            num_calls_second += 1
            called_second = True
            time.sleep(sleep_dur)
            return "second"

        @vault.automatic(threaded=True, input=KeyringAutomatic.trigger, output=KeyringAutomatic.third)
        def three(**kwargs):
            logger.info("three")
            nonlocal called_third
            nonlocal num_calls_third
            num_calls_third += 1
            called_third = True
            time.sleep(sleep_dur)
            return "third"

        @vault.manual(output=KeyringAutomatic.trigger)
        def start():
            return "go"

        @vault.automatic(input=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third),
                         output=KeyringAutomatic.final)
        def final(first, second, third):
            return first + second + third

        start()

        # If this fails, it's probably due to I/O contention. Try increasing the sleep duration.
        # KeyringAutomatic.final will be written to the vault sooner than it seems, but the different automatic functions
        # will lock the vault when they write, so a short sleep will mean the effect of I/O has a larger impact on the result.
        # Try increasing and lowering the sleep duration to see how it affects the duration of the test.
        vault.await_running_tasks(timeout=sleep_dur * 3, exception=TimeoutError(f"All tasks should have completed within {sleep_dur * 3} seconds. Methods appear to run in sequence"))

        assert len(vault.running_tasks) == 0, "All tasks should have completed and not be listed as running"
        # All functions should have been called
        assert called_first and vault.get(KeyringAutomatic.first) == "first"
        assert called_second and vault.get(KeyringAutomatic.second) == "second"
        assert called_third and vault.get(KeyringAutomatic.third) == "third"

        assert num_calls_first == 1
        assert num_calls_second == 1
        assert num_calls_third == 1

        with pytest.raises(ValueError) as e:
            @vault.automatic()
            async def async_func():
                pass

        assert f"Function test_automatic.async_func appears to be defined as async. Async functions do not work with automatic because async functions cannot truly run in the background. Use {vault.automatic.__name__} with 'threaded={True}' instead." in str(e.value)

    def test_automatic_threaded_existing_vault(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))
        vault.insert(KeyringAutomatic.trigger, "go")

        called_first = False
        num_calls_first = 0
        called_second = False
        num_calls_second = 0
        called_third = False
        num_calls_third = 0
        sleep_dur = 2

        vault_recreated = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="a"))

        @vault_recreated.automatic(threaded=True, input=KeyringAutomatic.trigger, output=KeyringAutomatic.first)
        def one(**kwargs):
            logger.info("one")
            nonlocal called_first
            nonlocal num_calls_first
            num_calls_first += 1
            called_first = True
            time.sleep(sleep_dur)
            return "first"

        @vault_recreated.automatic(threaded=True, input=KeyringAutomatic.trigger, output=KeyringAutomatic.second)
        def two(**kwargs):
            logger.info("two")
            nonlocal called_second
            nonlocal num_calls_second
            num_calls_second += 1
            called_second = True
            time.sleep(sleep_dur)
            return "second"

        @vault_recreated.automatic(threaded=True, input=KeyringAutomatic.trigger, output=KeyringAutomatic.third)
        def three(**kwargs):
            logger.info("three")
            nonlocal called_third
            nonlocal num_calls_third
            num_calls_third += 1
            called_third = True
            time.sleep(sleep_dur)
            logger.info("three done")
            return "third"

        @vault_recreated.automatic(input=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third),
                                   output=KeyringAutomatic.final)
        def final(first, second, third):
            return first + second + third

        # If this fails, it's probably due to I/O contention. Try increasing the sleep duration.
        # KeyringAutomatic.final will be written to the vault sooner than it seems, but the different automatic functions
        # will lock the vault when they write, so a short sleep will mean the effect of I/O has a larger impact on the result.
        # Try increasing and lowering the sleep duration to see how it affects the duration of the test.

        logger.info("Waiting for final...")
        while KeyringAutomatic.final not in vault_recreated:
            pass
        logger.info("Final value found in vault")

        vault_recreated.await_running_tasks(timeout=sleep_dur * 3, exception=TimeoutError(f"All tasks should have completed within {sleep_dur * 3} seconds. Methods appear to run in sequence"))

        assert len(vault_recreated.running_tasks) == 0, "All tasks should have completed and not be listed as running"
        # All functions should have been called
        assert called_first and vault_recreated.get(KeyringAutomatic.first) == "first"
        assert called_second and vault_recreated.get(KeyringAutomatic.second) == "second"
        assert called_third and vault_recreated.get(KeyringAutomatic.third) == "third"

        assert num_calls_first == 1
        assert num_calls_second == 1
        assert num_calls_third == 1

    def test_automatic_threaded_with_errors(self):
        vault = varvault.create(varvault.Flags.debug, keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))
        @vault.automatic(threaded=True, input=KeyringAutomatic.trigger, output=KeyringAutomatic.first)
        def one(**kwargs):
            logger.info("one")
            return "first"

        @vault.automatic(threaded=True, input=KeyringAutomatic.first, output=KeyringAutomatic.second)
        def two(**kwargs):
            logger.info("two")
            return "second"

        @vault.automatic(threaded=True, input=KeyringAutomatic.second, output=KeyringAutomatic.third)
        def three(**kwargs):
            raise Exception("three")

        vault.insert(KeyringAutomatic.trigger, "go")
        try:
            vault.await_running_tasks(timeout=10)
            pytest.fail(f"Should have raised an exception in {three.__name__}")
        except Exception as e:
            assert "three" in str(e)

    def test_automatic_threaded_with_sequential_flow(self):
        """
        This test will verify that the automatic decorator with the threaded flag set to True can run in sequence if each function should trigger the next one.
        Using something like a guard-thread that makes sure all threads complete should NOT be necessary. await_running_tasks should be sufficient.
        If this test fails, it could indicate a problem with ending all running tasks for the vault before triggering the next one in the sequence.
        :return:
        """
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault.automatic(threaded=True, input=KeyringAutomatic.trigger, output=KeyringAutomatic.first)
        def one(**kwargs):
            logger.info("one")
            return "first"

        @vault.automatic(threaded=True, input=KeyringAutomatic.first, output=KeyringAutomatic.second)
        def two(**kwargs):
            logger.info("two")
            return "second"

        @vault.automatic(threaded=True, input=KeyringAutomatic.second, output=KeyringAutomatic.third)
        def three(**kwargs):
            logger.info("three")
            return "third"

        @vault.automatic(input=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third),
                         output=KeyringAutomatic.final)
        def final(first, second, third):
            return first + second + third

        @vault.manual(output=KeyringAutomatic.trigger)
        def start():
            return "go"

        start()

        vault.await_running_tasks(timeout=10)

        assert len(vault.running_tasks) == 0, "All tasks should have completed and not be listed as running"

        assert vault.get(KeyringAutomatic.first) == "first"
        assert vault.get(KeyringAutomatic.second) == "second"
        assert vault.get(KeyringAutomatic.third) == "third"
        assert vault.get(KeyringAutomatic.final) == "firstsecondthird"

    def test_automatic_with_existing_vault(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))
        vault.insert(KeyringAutomatic.trigger, "go")

        vault_recreated = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="a"))

        # Registering this automatic will not trigger the function since the vault does not have the relevant keys yet, but will receive them
        @vault_recreated.automatic(input=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third),
                                   output=KeyringAutomatic.final)
        def final(first, second, third):
            return first + second + third

        # Registering this automatic will trigger the function immediately since the vault already has the relevant keys, which in turn will trigger the function above
        @vault_recreated.automatic(input=(KeyringAutomatic.trigger,),
                                   output=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third))
        def trigger_function(trigger: str = varvault.AssignedByVault):
            return "first", "second", "third"

        assert vault_recreated.get(KeyringAutomatic.final) == "firstsecondthird"

    def test_with_clean_keys(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))
        vault.insert(KeyringAutomatic.trigger, "go")

        vault_recreated = varvault.create(varvault.Flags.auto_run_regardless_of_key_status, keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="a"))

        # Registering this automatic will not trigger the function since the vault does not have the relevant keys yet, but will receive them
        @vault_recreated.automatic(input=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third),
                                   output=KeyringAutomatic.final)
        def final(first, second, third):
            return first + second + third

        # Registering this automatic will trigger the function immediately since the vault already has the relevant keys, which in turn will trigger the function above
        @vault_recreated.automatic(input=(KeyringAutomatic.trigger,),
                                   output=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third))
        def trigger_function(trigger: str = varvault.AssignedByVault):
            return "first", "second", "third"

        @vault_recreated.automatic(varvault.Flags.clean_output_keys,
                                   input=(KeyringAutomatic.final,),
                                   output=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third))
        def clean(final: str = varvault.AssignedByVault):
            return

        assert vault_recreated.get(KeyringAutomatic.final) == "firstsecondthird"
        assert vault_recreated.get(KeyringAutomatic.first) == ""
        assert vault_recreated.get(KeyringAutomatic.second) == ""
        assert vault_recreated.get(KeyringAutomatic.third) == ""

    def test_conditional(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))
        vault.insert(KeyringAutomatic.trigger, "go")

        vault_recreated = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="a"))

        # Registering this automatic will not trigger the function since the vault does not have the relevant keys yet, but will receive them
        @vault_recreated.automatic(input=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third),
                                   output=KeyringAutomatic.final)
        def final(first, second, third):
            return first + second + third

        did_not_get_called = True

        @vault_recreated.automatic(condition=lambda: vault_recreated.get(KeyringAutomatic.trigger) == "don't go",
                                   input=(KeyringAutomatic.trigger,),
                                   output=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third))
        def should_not_be_called(trigger: str = varvault.AssignedByVault):
            nonlocal did_not_get_called
            did_not_get_called = False
            logger.info(f"should_not_be_called: {trigger}")
            return "first", "second", "third"

        did_get_called = False

        @vault_recreated.automatic(condition=lambda: vault_recreated.get(KeyringAutomatic.trigger) == "go",
                                   input=(KeyringAutomatic.trigger,),
                                   output=(KeyringAutomatic.first, KeyringAutomatic.second, KeyringAutomatic.third))
        def should_be_called(trigger: str = varvault.AssignedByVault):
            nonlocal did_get_called
            did_get_called = True
            logger.info(f"should_be_called: {trigger}")
            return "first", "second", "third"

        assert did_not_get_called
        assert did_get_called
        assert vault_recreated.get(KeyringAutomatic.final) == "firstsecondthird"

    def test_output_replaces_input(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault.automatic(input=(KeyringAutomatic.trigger,),
                         output=(KeyringAutomatic.first,))
        def first(trigger: str = varvault.AssignedByVault):
            return "first"

        @vault.automatic(varvault.Flags.output_key_replaces_input_key,
                         input=(KeyringAutomatic.first,),
                         output=(KeyringAutomatic.second,))
        def second(first: str = varvault.AssignedByVault):
            assert first == "first"
            return "second"

        @vault.manual(varvault.Flags.output_key_replaces_input_key,
                      input=(KeyringAutomatic.trigger, KeyringAutomatic.second,),
                      output=(KeyringAutomatic.third,))
        def third(trigger: str = varvault.AssignedByVault,
                  second: str = varvault.AssignedByVault):
            assert trigger == "go"
            assert second == "second"
            return "third"

        vault.insert(KeyringAutomatic.trigger, "go")
        assert KeyringAutomatic.first not in vault
        assert KeyringAutomatic.first not in vault.writable_args
        assert vault.get(KeyringAutomatic.second) == "second"
        with pytest.raises(ValueError) as e:
            third()
        assert f"If {varvault.Flags.output_key_replaces_input_key} is defined, you MUST define exactly one input key and one output key." in str(e.value)

    def test_verify_input_output_cannot_contain_same_key(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))

        with pytest.raises(KeyError) as e:
            @vault.automatic(input=(KeyringAutomatic.trigger,),
                             output=(KeyringAutomatic.trigger,))
            def first(trigger: str = varvault.AssignedByVault):
                return "first"

        assert f"input and output cannot contain the same keys" in str(e.value)

    def test_with_permit_modifications(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault.automatic(varvault.Flags.permit_modifications, varvault.Flags.auto_run_regardless_of_key_status,
                         input=(KeyringAutomatic.trigger,),
                         output=(KeyringAutomatic.first,))
        def first(trigger: str = varvault.AssignedByVault):
            return trigger + "first"

        vault.insert(KeyringAutomatic.trigger, "go")
        assert vault.get(KeyringAutomatic.first) == "gofirst"
        vault.insert(KeyringAutomatic.trigger, "go-again", varvault.Flags.permit_modifications)
        assert vault.get(KeyringAutomatic.first) == "go-againfirst"

        with pytest.raises(KeyError) as e:
            @vault.automatic(varvault.Flags.auto_run_regardless_of_key_status,
                             input=(KeyringAutomatic.trigger,),
                             output=(KeyringAutomatic.first,))
            def new_first(trigger: str = varvault.AssignedByVault):
                return trigger + "first"
            vault.insert(KeyringAutomatic.trigger, "go-again", varvault.Flags.permit_modifications)
        # This should be triggered by the decorated function, hence why we check KeyringAutomatic.first is in the error string, not KeyringAutomatic.trigger.
        assert f"Key {KeyringAutomatic.first} already exists in the vault" in str(e.value)

    def test_keyless_automatic(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault.automatic(output=(KeyringAutomatic.first,))
        def first():
            return "first"

        assert vault.get(KeyringAutomatic.first) == "first"

        @vault.automatic(threaded=True, output=(KeyringAutomatic.second,))
        def second():
            return "second"

        while KeyringAutomatic.second not in vault:
            pass

        assert vault.get(KeyringAutomatic.second) == "second"

    def test_dont_run_automatic_if_exists(self):
        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="w"))
        vault.insert(KeyringAutomatic.first, "first")
        vault.insert(KeyringAutomatic.second, "second")

        vault = varvault.create(keyring=KeyringAutomatic, resource=varvault.JsonResource(vault_file_new, mode="a"))
        @vault.automatic(input=KeyringAutomatic.trigger, output=KeyringAutomatic.first)
        def first(trigger: str = varvault.AssignedByVault):
            raise Exception("first should not be called")

        @vault.automatic(input=KeyringAutomatic.trigger, output=KeyringAutomatic.second)
        def second(trigger: str = varvault.AssignedByVault):
            raise Exception("second should not be called")

        @vault.automatic(input=(KeyringAutomatic.first, KeyringAutomatic.second), output=KeyringAutomatic.final)
        def final(first, second):
            return first + second

        vault.insert(KeyringAutomatic.trigger, "go")
        assert vault.get(KeyringAutomatic.final) == "firstsecond"
