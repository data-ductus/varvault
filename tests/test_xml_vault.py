from typing import Union, Dict, List, AnyStr, Any, TextIO

import tempfile
import xmltodict

from commons import *


vault_file_new = f"{DIR}/new-vault.xml"
existing_vault = f"{DIR}/existing-vault.xml"


class XmlFileHandler(varvault.BaseFileHandler):
    KEY = "VAULT"

    def __init__(self, path: str, live_update=False, file_is_read_only=False):
        super(XmlFileHandler, self).__init__(path, live_update, file_is_read_only)

    @property
    def resource(self) -> TextIO:
        return self.file_io

    def create_resource(self, path: Union[AnyStr, Any]) -> None:
        if path and self.live_update and not os.path.exists(path):
            self.file_io = None
        elif path and not os.path.exists(path):
            # Create the file; It doesn't exist. Try to create the folder first.
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.file_io = open(path, "w")
            self.file_io.close()
        elif path and os.path.exists(path):
            # The file already exists; Just read from it
            self.file_io = open(path)
            self.file_io.close()
        else:
            raise NotImplementedError("This is not supported")

    @property
    def path(self) -> Union[AnyStr, Any]:
        return self.raw_path

    def kv_pair_can_be_written(self, obj: Dict) -> bool:
        obj = {self.KEY: obj}
        try:
            xmltodict.unparse(obj, pretty=True)
            return True
        except:
            return False

    def hash(self):
        import hashlib
        hash_md5 = hashlib.md5()
        with open(self.path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def do_write(self, vault: dict):
        # An XML file must have exactly one root. We assign the vault to the root self.KEY
        vault = {self.KEY: vault}
        xmltodict.unparse(vault, open(self.path, "w"), pretty=True)

    def do_read(self) -> Union[Dict, List]:
        vault = xmltodict.parse(open(self.path, "rb"))
        return vault[self.KEY]


class Keyring(varvault.Keyring):
    string_value = varvault.Key("string_value")
    int_value = varvault.Key("int_value")
    list_value = varvault.Key("list_value")


class TestXmlVault:
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

    def test_create_xml_vault(self):
        vault = varvault.create_vault(Keyring, "vault", varvault_filehandler_to=XmlFileHandler(vault_file_new))

        @vault.vaulter(return_keys=(Keyring.string_value, Keyring.int_value, Keyring.list_value))
        def _set():
            return "valid", 1, [1, 2, 3, 4, 5]

        _set()

        data_in_file = xmltodict.parse(open(vault_file_new, "rb"))[XmlFileHandler.KEY]
        logger.info(data_in_file)
        assert Keyring.string_value in data_in_file and data_in_file[Keyring.string_value] == "valid"
        # XML data is actually just strings. But we still want to support using XML files, but it will take some manual labour to get it working correctly.
        assert Keyring.int_value in data_in_file and data_in_file[Keyring.int_value] == "1"
        assert Keyring.list_value in data_in_file

    def test_read_from_xml_vault(self):
        vault = varvault.from_vault(Keyring, "vault-from", XmlFileHandler(existing_vault), varvault.VaultFlags.vault_is_read_only())

        @vault.vaulter(input_keys=(Keyring.string_value, Keyring.int_value))
        def _get(string_value=None, int_value=None):
            assert string_value == "valid"
            assert int_value == "1"

        _get()

