import os
from typing import Union, Dict, List

import sys
import logging
import tempfile
import xmltodict

import varvault
from varvault import BaseFileHandler


DIR = os.path.dirname(os.path.realpath(__file__))
path = f"{os.path.dirname(DIR)}"
temp_path = [path]
temp_path.extend(sys.path)
sys.path = temp_path

logger = logging.getLogger("pytest")
vault_file_new = f"{DIR}/new-vault.xml"
existing_vault = f"{DIR}/existing-vault.xml"


class XmlFileHandler(BaseFileHandler):
    KEY = "VAULT"

    def __init__(self, filename: str, live_update=False, file_is_read_only=False):
        super(XmlFileHandler, self).__init__(filename, live_update, file_is_read_only)

    def do_write(self, vault: dict):
        # An XML file must have exactly one root. We assign the vault to the root self.KEY
        vault = {self.KEY: vault}
        xmltodict.unparse(vault, open(self.file.name, "w"), pretty=True)

    def do_read(self) -> Union[Dict, List]:
        vault = xmltodict.parse(open(self.file.name, "rb"))
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
        vault = varvault.create_vault(Keyring, "vault", varvault_vault_filename_to=vault_file_new, varvault_filehandler_class=XmlFileHandler)

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
        vault = varvault.from_vault(Keyring, "vault-from", existing_vault, XmlFileHandler, varvault.VaultFlags.file_is_read_only())

        @vault.vaulter(input_keys=(Keyring.string_value, Keyring.int_value))
        def _get(string_value=None, int_value=None):
            assert string_value == "valid"
            assert int_value == "1"

        _get()

