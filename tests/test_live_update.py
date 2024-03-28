import json
import tempfile
import threading
import time

from commons import *
from tests.notif_reader import NotifReader

vault_file_new = f"{DIR}/new-vault.json"
vault_file_new_secondary = f"{DIR}/new-vault-secondary.json"


class TestLiveUpdate:

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
        try:
            os.remove(vault_file_new + ".bak")
        except:
            pass

    def test_live_update_vault(self):
        vault_new = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w+"))
        vault_from = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="r+"))

        @vault_new.manual(output=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert Keyring.key_valid_type_is_str not in vault_from, f"{Keyring.key_valid_type_is_str} already in the vault; This should not be the case"

        @vault_from.manual(input=Keyring.key_valid_type_is_str)
        def _get(**kwargs):
            v = kwargs.get(Keyring.key_valid_type_is_str)
            assert v == "valid", f"Value {v} is not correct; Live-update doesn't work"
        _get()

    def test_live_update_on_main_vault(self):
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w+"))

        @vault.manual(output=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert Keyring.key_valid_type_is_int not in vault, f"{Keyring.key_valid_type_is_int} already in vault; This should not be possible"

        vault_data = json.load(open(vault_file_new))
        vault_data[Keyring.key_valid_type_is_int] = 1
        json.dump(vault_data, open(vault_file_new, "w"), indent=2)

        assert Keyring.key_valid_type_is_int not in vault, f"{Keyring.key_valid_type_is_int} already in vault; This should not be possible"

        @vault.manual(input=Keyring.key_valid_type_is_int)
        def _get(**kwargs):
            key_valid_type_is_int = kwargs.get(Keyring.key_valid_type_is_int)
            assert key_valid_type_is_int == 1
        _get()

    def test_create_live_update_vault(self):
        assert not os.path.exists(vault_file_new)
        # The file should NOT be created here
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="r+"))
        assert not os.path.exists(vault_file_new)
        # Here the file SHOULD be created
        vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w+"))
        assert os.path.exists(vault_file_new)
        assert Keyring.key_valid_type_is_str not in vault
        assert Keyring.key_valid_type_is_int not in vault

        json.dump({Keyring.key_valid_type_is_str: "valid", Keyring.key_valid_type_is_int: 1}, open(vault_file_new, "w"))

        assert vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert vault.get(Keyring.key_valid_type_is_int) == 1

    def test_threaded_vaults_live_update(self):
        def runner():
            vault_thread = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
            vault_thread.insert(Keyring.key_valid_type_is_str, "valid")
            vault_thread.insert(Keyring.key_valid_type_is_int, 1)

        assert not os.path.exists(vault_file_new)
        vault_outer = varvault.create(keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="r+"))
        assert not os.path.exists(vault_file_new), "Vault file is created when it shouldn't be"

        t = threading.Thread(target=runner)
        t.start()
        t.join()

        @vault_outer.manual(input=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def validate(key_valid_type_is_str=None, key_valid_type_is_int=None):
            assert key_valid_type_is_str == "valid"
            assert key_valid_type_is_int == 1
        validate()

    def test_resource_live_update(self):
        resource = varvault.JsonResource(vault_file_new, mode="w+")
        assert not resource.exists()
        resource.create()
        assert resource.exists()
        pre_state = resource.state
        json.dump({Keyring.key_valid_type_is_str: "valid", Keyring.key_valid_type_is_int: 1}, open(vault_file_new, "w"))
        assert resource.resource_has_changed()
        assert resource.cached_state != pre_state
        data = resource.read()
        assert data[Keyring.key_valid_type_is_str] == "valid"
        assert data[Keyring.key_valid_type_is_int] == 1
        resource.update_state()

        assert resource.last_known_state == resource.cached_state


class TestConcurrency:
    def test_read_write_concurrency(self):
        """
        Test to start a process to write to a file, then have multiple threads reading that file for changes.

        :return:
        """
        attempts = 100
        attempts_made = 0
        while attempts_made < attempts:
            services = 1000
            service_list = [f"service-{n}" for n in range(services)]
            notif_reader = NotifReader(vault_path=vault_file_new_secondary, services=services, do_sleep=False)
            timeout = services
            start = time.time()
            services_found = list()
            def find_notifs(service):
                notifs = None
                while not notifs and time.time() - start < timeout:
                    notifs = notif_reader.get_notifs(service)
                varvault.assert_and_raise(notifs is not None, TimeoutError(f"Service-{service} not found in {timeout} seconds"))
                services_found.append(notifs['service'])

            varvault.threaded_execution([varvault.create_function(find_notifs, service) for service in service_list], max_workers=int(services / 10))

            assert len(services_found) == services, f"Expected {services} services, but found {len(services_found)}"
            assert all([service in services_found for service in service_list]), f"Expected all services to be found, but some were missing"
            attempts_made += 1
            logger.info(f"Attempt {attempts_made} successful")
