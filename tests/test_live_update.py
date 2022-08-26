import json
import tempfile
import threading

from commons import *


vault_file_new = f"{DIR}/new-vault.json"
vault_file_new_secondary = f"{DIR}/new-vault-secondary.json"


class TestLiveUpdate:

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

    def test_live_update_vault(self):
        vault_new = varvault.create_vault(Keyring, "vault", varvault_resource_to=varvault.JsonResource(vault_file_new))
        vault_from = varvault.from_vault(Keyring, "vault-from", varvault.JsonResource(vault_file_new), varvault.VaultFlags.live_update(), varvault.VaultFlags.vault_is_read_only())

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

    def test_live_update_on_main_vault(self):
        vault = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.live_update(), varvault_resource_to=varvault.JsonResource(vault_file_new, create_file_on_live_update=True))

        @vault.vaulter(return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert Keyring.key_valid_type_is_int not in vault, f"{Keyring.key_valid_type_is_int} already in vault; This should not be possible"

        vault_data = json.load(open(vault_file_new))
        vault_data[Keyring.key_valid_type_is_int] = 1
        json.dump(vault_data, open(vault_file_new, "w"), indent=2)

        assert Keyring.key_valid_type_is_int not in vault, f"{Keyring.key_valid_type_is_int} already in vault; This should not be possible"

        @vault.vaulter(input_keys=Keyring.key_valid_type_is_int)
        def _get(**kwargs):
            key_valid_type_is_int = kwargs.get(Keyring.key_valid_type_is_int)
            assert key_valid_type_is_int == 1
        _get()

    def test_create_live_update_vault(self):
        assert not os.path.exists(vault_file_new)
        # The file should NOT be created here
        vault = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.live_update(), varvault_resource_to=varvault.JsonResource(vault_file_new))
        assert not os.path.exists(vault_file_new)
        # Here the file SHOULD be created
        vault = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.live_update(), varvault_resource_to=varvault.JsonResource(vault_file_new, create_file_on_live_update=True))
        assert os.path.exists(vault_file_new)
        assert Keyring.key_valid_type_is_str not in vault
        assert Keyring.key_valid_type_is_int not in vault

        json.dump({Keyring.key_valid_type_is_str: "valid", Keyring.key_valid_type_is_int: 1}, open(vault_file_new, "w"))

        assert vault.get(Keyring.key_valid_type_is_str) == "valid"
        assert vault.get(Keyring.key_valid_type_is_int) == 1

    def test_threaded_vaults_live_update(self):
        def runner():
            vault_thread = varvault.create_vault(Keyring, "thread", varvault_resource_to=varvault.JsonResource(vault_file_new))
            vault_thread.insert(Keyring.key_valid_type_is_str, "valid")
            vault_thread.insert(Keyring.key_valid_type_is_int, 1)

        assert not os.path.exists(vault_file_new)
        vault_outer = varvault.from_vault(Keyring, "outer", varvault.JsonResource(vault_file_new), varvault.VaultFlags.live_update())
        assert not os.path.exists(vault_file_new), "Vault file is created when it shouldn't be"

        t = threading.Thread(target=runner)
        t.start()
        t.join()

        @vault_outer.vaulter(input_keys=(Keyring.key_valid_type_is_str, Keyring.key_valid_type_is_int))
        def validate(key_valid_type_is_str=None, key_valid_type_is_int=None):
            assert key_valid_type_is_str == "valid"
            assert key_valid_type_is_int == 1
        validate()

    def test_filehandler_live_update(self):
        fh = varvault.JsonResource(vault_file_new, live_update=True, create_file_on_live_update=True)
        assert not fh.exists()
        fh.create_resource()
        assert fh.exists()
        pre_state = fh.state
        json.dump({Keyring.key_valid_type_is_str: "valid", Keyring.key_valid_type_is_int: 1}, open(vault_file_new, "w"))
        assert fh.resource_has_changed()
        assert fh.cached_state != pre_state
        data = fh.read()
        assert data[Keyring.key_valid_type_is_str] == "valid"
        assert data[Keyring.key_valid_type_is_int] == 1
        fh.update_state()

        assert fh.last_known_state == fh.cached_state
