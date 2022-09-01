__version__ = "4.1.0"


import os
import json

from typing import Dict, TextIO, AnyStr

from .resource import BaseResource

from .keyring import Key
from .keyring import Keyring

from .validator import validator

from .minivault import MiniVault

from .vault import VarVault

from .vaultflags import VaultFlags

from .vaultfactory import create_vault
from .vaultfactory import from_vault

from .vaultstructs import VaultStructDictBase
from .vaultstructs import VaultStructListBase
from .vaultstructs import VaultStructFloatBase
from .vaultstructs import VaultStructIntBase
from .vaultstructs import VaultStructStringBase

from .utils import AssignedByVault
from .utils import concurrent_execution
from .utils import create_mv_from_resource


def clear_logs():
    import glob
    import tempfile

    path = os.path.join(tempfile.tempdir, "varvault-logs", "*.log")
    files = glob.glob(path)
    for f in files:
        os.remove(f)


class JsonResource(BaseResource):

    def __init__(self, path: AnyStr, live_update=False, vault_is_read_only=False, create_file_on_live_update=False):
        """
        Creates the JsonFileHandler object.
        :param path: This should be the path to the JSON file that the vault should be using.
        :param live_update: An optional flag to say if we should do live-update on the vault. Essentially, a vault can be created where either the file or the object in memory is in
          charge of the state of the vault. This flag gives the file the ownership of the vault.
        :param vault_is_read_only: An optional flag to say if we are only allowed to read from the vault and never do any changes to the file.
        :param create_file_on_live_update: An optional flag specific for this filehandler. It tells if we should create the file when we use live-update or not.
          Normally, you'd expect the file to be created by something, or someone, else.
        """
        path = os.path.expanduser(os.path.expandvars(path))
        self.file_io = None
        self.create_file_on_live_update = create_file_on_live_update
        super(JsonResource, self).__init__(path, live_update, vault_is_read_only)

    @property
    def state(self):
        """Returns the state of the vault, which is the state of the JSON file"""
        import hashlib
        hash_md5 = hashlib.md5()
        with open(self.path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @property
    def resource(self) -> TextIO:
        """Returns the file resource object for this handler."""
        return self.file_io

    def create_resource(self) -> None:
        """Creates the resource self.file_io for this handler which we'll use to read and write to."""
        path = self.path
        assert path, "Path is not defined"
        dir = os.path.dirname(path)
        if dir:
            os.makedirs(dir, exist_ok=True)

        def create():
            file_io = open(path, "w")
            json.dump({}, file_io, indent=2)
            file_io.close()
            return file_io

        self.file_io = None
        if self.exists():
            self.file_io = open(path, "r+")
        elif not self.live_update:
            self.file_io = create()
        elif self.create_file_on_live_update:
            self.file_io = create()

    @property
    def path(self) -> AnyStr:
        """Returns the path to the vault-file as a JSON file."""
        return self.raw_path

    def writable(self, obj: Dict) -> bool:
        f"""Checks if a key-value pair in a dict can be written to a file by attempting to serialize it by using {json.dumps}"""
        try:
            json.dumps(obj)
            return True
        except (TypeError, OverflowError) as e:
            return False

    def exists(self) -> bool:
        """Returns a bool that determines if the JSON file exists by expanding user and potential vars"""
        return os.path.exists(self.path)

    def do_write(self, vault: dict) -> None:
        """Writes the vault to the JSON file"""
        json.dump(vault, open(self.path, "w"), indent=2)

    def do_read(self) -> Dict:
        """Reads the vault from the JSON file"""
        return json.load(open(self.path))
