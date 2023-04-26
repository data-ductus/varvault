import tempfile

import varvault.logger
from commons import *


vault_file_new = f"{DIR}/new-vault.json"
vault_file_new_secondary = f"{DIR}/new-vault-secondary.json"


class TestLogging:
    @classmethod
    def setup_class(cls):
        tempfile.tempdir = "/tmp" if sys.platform == "darwin" or sys.platform == "linux" else tempfile.gettempdir()

    def setup_method(self):
        try:
            temp_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault-stream.log")
            os.remove(temp_log_file)
        except:
            pass

        try:
            vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault.log")
            os.remove(vault_log_file)
        except:
            pass

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
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault.log")
        vault_new = varvault.create(varvault.Flags.silent, varvault.Flags.remove_existing_log_file, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        vault_new.logger.addHandler(logging.StreamHandler(open(temp_log_file, "w")))

        @vault_new.manual(output=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()
        assert len(open(temp_log_file).readlines()) <= 2, f"There appears to be more lines in the log file than what there should be. " \
                                                          f"There should only be 2 at most. {varvault.Flags.silent} appears to not function correctly"
        assert len(open(vault_log_file).readlines()) <= 2, f"There appears to be more lines in the log file than what there should be. " \
                                                           f"There should only be 2 at most. {varvault.Flags.silent} appears to not function correctly. " \
                                                           f"Contents: \n{open(vault_log_file).readlines()}"

    def test_debug(self):
        temp_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault-stream.log")
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault.log")
        vault_new = varvault.create(varvault.Flags.debug, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        # Create and set a file to act as a StreamHandler for the logger object in varvault.
        # This way, we can easily capture stdout to a file and assert that the output is the expected
        vault_new.logger.addHandler(logging.StreamHandler(open(temp_log_file, "w")))

        @vault_new.manual(output=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert len(open(temp_log_file).readlines()) >= 10, f"There appears to be fewer lines in the log file than what there should be. " \
                                                           f"There should only be 12 at least. {varvault.Flags.debug} appears to not function correctly"
        assert len(open(vault_log_file).readlines()) >= 12, f"There appears to be fewer lines in the log file than what there should be. " \
                                                            f"There should only be 12 at least. {varvault.Flags.debug} appears to not function correctly"

        @vault_new.manual(input=Keyring.key_valid_type_is_str)
        def _use(key_valid_type_is_str: str = varvault.AssignedByVault):
            return key_valid_type_is_str

        assert _use() == "valid", "The value returned by the function is not the same as the value that was set"

    def test_silent_and_debug(self):
        temp_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault-stream.log")
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault.log")
        vault_new = varvault.create(varvault.Flags.debug, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        # Create and set a file to act as a StreamHandler for the logger object in varvault.
        # This way, we can easily capture stdout to a file and assert that the output is the expected
        vault_new.logger.addHandler(logging.StreamHandler(open(temp_log_file, "w")))

        @vault_new.manual(varvault.Flags.silent, output=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()

        assert len(open(temp_log_file).readlines()) == 0, f"There appears to be more lines in the log file than what there should be. " \
                                                          f"There should be 0 at most. {varvault.Flags.debug} with {varvault.Flags.silent} appears to not function correctly"
        assert len(open(vault_log_file).readlines()) == 12, f"There appears to be fewer lines in the log file than what there should be. " \
                                                            f"There should be 12 at most. {varvault.Flags.debug} with {varvault.Flags.silent} appears to not function correctly"

    def test_disable_logger(self):
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault.log")
        try:
            os.unlink(vault_log_file)
        except OSError:
            pass
        assert not os.path.exists(vault_log_file), f"{vault_log_file} still exists, weird"

        vault_new = varvault.create(varvault.Flags.disable_logger, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        assert vault_new.logger is None, "logger object is not None; it should be"
        assert not os.path.exists(vault_log_file), f"{vault_log_file} exists after creating the vault when saying there shouldn't be a logger object"

        @vault_new.manual(varvault.Flags.silent, output=Keyring.key_valid_type_is_str)
        def _set():
            return "valid"
        _set()
        assert not os.path.exists(vault_log_file), f"{vault_log_file} exists after using the vault. How?!"

    def test_remove_existing_log_file(self):
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault.log")
        vault_new = varvault.create(varvault.Flags.debug, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))

        @vault_new.manual(varvault.Flags.silent, output=Keyring.key_valid_type_is_str)
        def _doset():
            return "valid"
        _doset()
        with open(vault_log_file) as f1:
            vault_log_file_lines = f1.readlines()
            assert len(vault_log_file_lines) == 12, f"There should be exactly 12 lines in the log-file:\n{''.join(vault_log_file_lines)}"
        vault_from = varvault.create(varvault.Flags.remove_existing_log_file, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="r"))
        assert Keyring.key_valid_type_is_str in vault_from
        with open(vault_log_file) as f2:
            vault_log_file_lines = f2.readlines()
            assert len(vault_log_file_lines) == 2, f"There should be exactly 2 lines in the logfile. It seems the log-file wasn't removed when the new vault was created from the existing vault: \n{''.join(vault_log_file_lines)}"

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

            vault_new = varvault.create(varvault.Flags.debug, varvault.Flags.remove_existing_log_file, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"), logger=logger)
            assert vault_new.logger.name == "pytest"  # The logger used for pytest here is called pytest

            @vault_new.manual(varvault.Flags.silent, output=Keyring.key_valid_type_is_str)
            def _set():
                return "valid"
            _set()
            temp_log_file_lines = open(temp_log_file).readlines()
            assert len(temp_log_file_lines) == 1, f"There appears to be more lines in the log file than what there should be. There should be 1 at most. \n{''.join(temp_log_file_lines)}"
            vault_log_file_lines = open(vault_log_file).readlines()
            assert len(vault_log_file_lines) == 11, f"There appears to be fewer lines in the log file than what there should be. There should be 11 at most. \n{''.join(vault_log_file_lines)}"

        finally:
            logger.handlers.clear()
            logger.handlers = old_handlers

    def test_no_error_logging(self):
        temp_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault-vault-stream.log")
        vault_log_file = os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault.log")
        vault_new = varvault.create(varvault.Flags.debug, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        # Create and set a file to act as a StreamHandler for the logger object in varvault.
        # This way, we can easily capture stdout to a file and assert that the output is the expected
        vault_new.logger.addHandler(logging.StreamHandler(open(temp_log_file, "w")))

        @vault_new.manual(varvault.Flags.no_error_logging, output=Keyring.key_valid_type_is_str)
        def _set():
            raise Exception("Failing deliberately")

        try:
            _set()
        except:
            pass

        assert len(open(temp_log_file).readlines()) == 3, f"There appears to be more lines in the log file than what there should be. " \
                                                          f"There should be 3 at most. It appears that {varvault.Flags.no_error_logging} doesn't work properly"
        assert len(open(vault_log_file).readlines()) == 5, f"There appears to be fewer lines in the log file than what there should be. " \
                                                           f"There should be 5 at most. It appears that {varvault.Flags.no_error_logging} doesn't work properly"

    def test_clear_logs(self):
        vault = varvault.create(varvault.Flags.debug, keyring=Keyring, resource=varvault.JsonResource(vault_file_new, mode="w"))
        varvault.clear_logs()
        assert not os.path.exists(os.path.join(tempfile.gettempdir(), "varvault-logs", "varvault.log")), f"The log file still exists after calling {varvault.clear_logs.__name__}"