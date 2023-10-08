__version__ = "6.0.2"

import os
import json

from typing import Dict, TextIO, AnyStr, Literal, Union

from .resource import ResourceModes
from .resource import BaseResource
from .resource import ResourceNotFoundError

from .keyring import Key
from .keyring import Keyring

from .validator import validator
from .validator import modifier
from .validator import ValidatorException
from .validator import ModifierException

from .minivault import MiniVault

from .vault import VarVault

from .flags import Flags

from .factory import create

from .vaultstructs import VaultStructDictBase
from .vaultstructs import VaultStructListBase
from .vaultstructs import VaultStructFloatBase
from .vaultstructs import VaultStructIntBase
from .vaultstructs import VaultStructStringBase

from .utils import AssignedByVault
from .utils import concurrent_execution
from .utils import assert_and_raise


def clear_logs():
    import glob
    import tempfile

    path = os.path.join(tempfile.tempdir, "varvault-logs", "*.log")
    files = glob.glob(path)
    for f in files:
        os.remove(f)


class JsonResource(BaseResource):

    def __init__(self, path: AnyStr, mode: Union[Literal["r", "w", "a", "r+", "w+", "a+"], ResourceModes] = "r"):
        f"""
        Creates the JsonResource object.
        :param path: This should be the path to the JSON file that the vault should be using.
        :param mode: Sets the mode of the resource. The mode can be one of the following: 'r', 'w', 'a', 'r+', 'w+', 'a+'.
        r: Read from existing resource (default)
        w: Create new resource and ignore existing resource and write to it
        a: Create a new resource if none exist, otherwise read from and write to existing resource
        r+: Read from existing resource and perform live-update
        w+: Create new resource and ignore existing resource and write to it, and perform live-update
        a+: Create a new resource if none exist, otherwise read from and write to existing resource, and perform live-update
        """
        super(JsonResource, self).__init__(path, mode)
        self.file_io = None

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

    def create(self) -> None:
        """Creates the resource self.file_io for this handler which we'll use to read and write to."""
        path = self.path
        assert path, "Path is not defined"
        dirname = os.path.dirname(path)

        create_dir = lambda: os.makedirs(dirname, exist_ok=True) if dirname else None
        write = lambda: self.do_write({})

        if self.mode_properties.create and not self.mode_properties.load:
            create_dir()
            write()

        elif self.mode_properties.load and self.mode_properties.create:
            if not self.exists():
                create_dir()
                write()
        else:
            assert_and_raise(self.mode_properties.load and not self.mode_properties.create, NotImplementedError(f"Mode {self.mode} is not valid ({self.mode_properties})"))
            try:
                self.do_read()
            except Exception as e:
                if not self.mode_properties.live_update:
                    raise ResourceNotFoundError(f"Unable to read from resource at {path} (mode is {self.mode})", self) from e
                else:
                    return

        self.file_io = open(self.path, "r+")
        self.file_io.close()

    @property
    def backup(self):
        """Returns the backup path for this handler"""
        return self.raw_path + ".bak"

    @property
    def path(self) -> AnyStr:
        """Returns the path to the vault-file as a JSON file."""
        return self.raw_path if os.path.exists(self.raw_path) else self.backup

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
        with open(self.backup, "w") as f:
            json.dump(vault, f, indent=2)
        os.rename(self.backup, self.raw_path)

    def do_read(self) -> Dict:
        """Reads the vault from the JSON file"""
        return json.load(open(self.path))
