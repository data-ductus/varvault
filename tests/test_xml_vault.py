from typing import Union, Dict, List, AnyStr, Any, TextIO

import tempfile
import xmltodict

from commons import *


vault_file_new = f"{DIR}/new-vault.xml"
existing_vault = f"{DIR}/existing-vault.xml"


class XmlResource(varvault.BaseResource):

    KEY = "VAULT"

    def __init__(self, path: str, live_update=False, file_is_read_only=False):
        self.file_io = None
        super(XmlResource, self).__init__(path, live_update, file_is_read_only)

    @property
    def resource(self) -> TextIO:
        return self.file_io

    def create_resource(self) -> None:
        path = self.path
        assert path, "Path is not defined"
        os.makedirs(os.path.dirname(path), exist_ok=True)

        def create():
            file_io = open(path, "w")
            file_io.close()
            return file_io

        self.file_io = None
        if self.exists():
            self.file_io = open(path, "r+")
        elif not self.live_update:
            self.file_io = create()

    @property
    def state(self):
        import hashlib
        hash_md5 = hashlib.md5()
        with open(self.path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @property
    def path(self) -> Union[AnyStr, Any]:
        return self.raw_path

    def writable(self, obj: Dict) -> bool:
        obj = {self.KEY: obj}
        try:
            xmltodict.unparse(obj, pretty=True)
            return True
        except:
            return False

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
        vault = varvault.create_vault(Keyring, "vault", varvault_resource_to=XmlResource(vault_file_new))

        @vault.vaulter(return_keys=(Keyring.string_value, Keyring.int_value, Keyring.list_value))
        def _set():
            return "valid", 1, [1, 2, 3, 4, 5]

        _set()

        data_in_file = xmltodict.parse(open(vault_file_new, "rb"))[XmlResource.KEY]
        logger.info(data_in_file)
        assert Keyring.string_value in data_in_file and data_in_file[Keyring.string_value] == "valid"
        # XML data is actually just strings. But we still want to support using XML files, but it will take some manual labour to get it working correctly.
        assert Keyring.int_value in data_in_file and data_in_file[Keyring.int_value] == "1"
        assert Keyring.list_value in data_in_file

    def test_read_from_xml_vault(self):
        vault = varvault.from_vault(Keyring, "vault-from", XmlResource(existing_vault), varvault.VaultFlags.vault_is_read_only())

        @vault.vaulter(input_keys=(Keyring.string_value, Keyring.int_value))
        def _get(string_value=None, int_value=None):
            assert string_value == "valid"
            assert int_value == "1"

        _get()

