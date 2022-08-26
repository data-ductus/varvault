import tempfile


from commons import *


vault_file_new = f"{DIR}/new-vault.json"
vault_file_new_secondary = f"{DIR}/new-vault-secondary.json"


class TestLogging:
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

    def test_silent(self):
        temp_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault-stream.log")
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault.log")
        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.silent(), varvault_resource_to=varvault.JsonResource(vault_file_new))
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
        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.debug(), varvault_resource_to=varvault.JsonResource(vault_file_new))
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
        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.debug(), varvault_resource_to=varvault.JsonResource(vault_file_new))
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

        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.disable_logger(), varvault_resource_to=varvault.JsonResource(vault_file_new))
        assert vault_new.logger is None, "logger object is not None; it should be"
        assert not os.path.exists(vault_log_file), f"{vault_log_file} exists after creating the vault when saying there shouldn't be a logger object"

        @vault_new.vaulter(varvault.VaultFlags.silent(), return_keys=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()
        assert not os.path.exists(vault_log_file), f"{vault_log_file} exists after using the vault. How?!"

    def test_remove_existing_log_file(self):
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault.log")
        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.debug(), varvault_resource_to=varvault.JsonResource(vault_file_new))

        @vault_new.vaulter(varvault.VaultFlags.silent(), return_keys=Keyring.key_valid_type_is_str)
        def _doset():
            return "valid"
        _doset()
        with open(vault_log_file) as f1:
            assert len(f1.readlines()) == 12, f"There should be exactly 12 lines in the log-file."
        vault_from = varvault.from_vault(Keyring, "vault", varvault.JsonResource(vault_file_new), varvault.VaultFlags.remove_existing_log_file())
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

            vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.debug(), varvault_resource_to=varvault.JsonResource(vault_file_new), varvault_specific_logger=logger)
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

    def test_no_error_logging(self):
        temp_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault-stream.log")
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault.log")
        vault_new = varvault.create_vault(Keyring, "vault", varvault.VaultFlags.debug(), varvault_resource_to=varvault.JsonResource(vault_file_new))
        # Create and set a file to act as a StreamHandler for the logger object in varvault.
        # This way, we can easily capture stdout to a file and assert that the output is the expected
        vault_new.logger.addHandler(logging.StreamHandler(open(temp_log_file, "w")))

        @vault_new.vaulter(varvault.VaultFlags.no_error_logging(), return_keys=Keyring.key_valid_type_is_str)
        def _set():
            raise Exception("Failing deliberately")

        try:
            _set()
        except:
            pass

        assert len(open(temp_log_file).readlines()) == 3, f"There appears to be more lines in the log file than what there should be. " \
                                                          f"There should be 3 at most. It appears that {varvault.VaultFlags.no_error_logging()} doesn't work properly"
        assert len(open(vault_log_file).readlines()) == 5, f"There appears to be fewer lines in the log file than what there should be. " \
                                                           f"There should be 5 at most. It appears that {varvault.VaultFlags.no_error_logging()} doesn't work properly"