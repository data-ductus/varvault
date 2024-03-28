from typing import Union, Dict, List, AnyStr, Any, TextIO, Literal

import tempfile
import xmltodict

from commons import *
from varvault import ResourceNotFoundError

vault_file_new = f"{DIR}/new-vault.xml"
existing_vault = f"{DIR}/existing-vault.xml"


class XmlResource(varvault.BaseResource):

    KEY = "VAULT"

    def __init__(self, path: str, mode: Literal["r", "w", "a", "r+", "w+", "a+"] = "r"):
        self.file_io = None
        super(XmlResource, self).__init__(path, mode)

    @property
    def resource(self) -> TextIO:
        return self.file_io

    def dir_of_path(self) -> str:
        return os.path.dirname(self.path) or os.getcwd()

    def read_mode(self):
        varvault.assert_and_raise(os.path.exists(self.path), ResourceNotFoundError(f"Unable to read from resource at {self.path} (mode is {self.mode})", self))
        self.file_io = open(self.path, "r")
        self.file_io.close()

    def write_mode(self):
        os.makedirs(self.dir_of_path(), exist_ok=True)
        self.file_io = open(self.path, "w")
        self.file_io.close()
        self.do_write({})

    def append_mode(self):
        os.makedirs(self.dir_of_path(), exist_ok=True)
        self.file_io = open(self.path, "a")
        self.file_io.close()
        self.do_write({})

    def read_live_update_mode(self):
        os.makedirs(self.dir_of_path(), exist_ok=True)
        if os.path.exists(self.path):
            self.read_mode()

    def write_live_update_mode(self):
        self.write_mode()

    def append_live_update_mode(self):
        self.append_mode()

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
        tempfile.tempdir = "/tmp" if sys.platform == "darwin" or sys.platform == "linux" else tempfile.gettempdir()

    def setup_method(self):
        try:
            os.remove(vault_file_new)
        except:
            pass

    def test_create_xml_vault(self):
        vault = varvault.create(keyring=Keyring, resource=XmlResource(vault_file_new, mode="w"))

        @vault.manual(output=(Keyring.string_value, Keyring.int_value, Keyring.list_value))
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
        vault = varvault.create(keyring=Keyring, resource=XmlResource(existing_vault, "r"))

        @vault.manual(input=(Keyring.string_value, Keyring.int_value))
        def _get(string_value=None, int_value=None):
            assert string_value == "valid"
            assert int_value == "1"

        _get()

