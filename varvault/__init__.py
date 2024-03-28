# Version handling
# A good way to tell if we are backwards compatible is to run the test suite and if the tests pass without requiring any changes, we can pretty safely assume we are backwards compatible.
MAJOR = 7  # Change this if the previous MAJOR is incompatible with this build. Set MINOR and PATCH to 0
MINOR = 0  # Change this if the functionality has changed, but we are still backwards compatible with previous MINOR versions. Set PATCH to 0
PATCH = 0  # Change this is if we are fixing a bug that doesn't change the functionality. If a bug-fix has caused functionality to be changed, see MINOR instead
__version__ = f"{MAJOR}.{MINOR}.{PATCH}"

import logging
import os
import json
import warnings

from typing import Dict, TextIO, AnyStr, Literal, Union, Type

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

from .vaultstructs import VaultStructDictBase
from .vaultstructs import VaultStructListBase
from .vaultstructs import VaultStructFloatBase
from .vaultstructs import VaultStructIntBase
from .vaultstructs import VaultStructStringBase

from .threadgroup import ThreadGroup
from .threadgroup import create_function
from .threadgroup import create_functions
from .threadgroup import threaded_execution

from .structs import ResultStruct
from .structs import ResultList
from .structs import Function

from .utils import AssignedByVault
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

    def dir_of_path(self):
        return os.path.abspath(os.path.dirname(self.path) or os.getcwd())

    def read_mode(self):
        assert_and_raise(os.path.exists(self.path), ResourceNotFoundError(f"Unable to read from resource at {self.path} (mode is {self.mode})", self))
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


def create(*flags: Flags,
           keyring: Type[Keyring] = None,
           name: str = None,
           resource: BaseResource = None,
           logger: logging.Logger = None,
           **extra_keys: Key) -> VarVault:
    f"""
    Factory-function to help create a Vault-object instead of creating it manually (which is still possible).

    :param keyring: Describes which keys belong to this Vault.
    :param name: Optional. Used to name the vault and the logger for writing information and debug messages, unless {logger} was passed.
    :param resource: Optional resource to read/write the vault from/to respectively.
    :param flags: Optional arguments for defining {Flags} for this Vault.
     Note that any global {Flags} will be overridden by {Flags} defined in a vault-decorator.
    :param logger: Optional argument for defining your own logger object if you want to use a specific logger rather than varvault's own logger.
    :param extra_keys: Extra keys as a dict to write to. These keys can be defined during runtime, which can sometimes be necessary.
     It is recommended to use pre-determined keys (e.g. constants), but sometimes being more flexible can be useful.
    :return: Vault object based on input to this function.
    """
    faulty_keys = [k for k, v in extra_keys.items() if not isinstance(v, Key)]
    if faulty_keys:
        raise ValueError(f"Extra keys must be of type Key. Faulty keys that must be changed: {faulty_keys}")
    extra_keys_cleaned = {str(v.key_name): v for _, v in extra_keys.items()}
    extra_keys = extra_keys_cleaned
    initial_vars = None
    if resource and resource.mode_properties.load:
        vault_file_data = resource.read()

        assert isinstance(vault_file_data, dict), f"It appears we were not able to load a Dict from {resource}. Are you sure this is a valid resource? (content={vault_file_data})"
        keys_in_keyring = keyring.get_keys()
        keys_in_keyring.update(extra_keys)
        keys_in_file = vault_file_data.keys()
        _keys_not_in_keyring = [k for k in keys_in_file if k not in keys_in_keyring]
        if _keys_not_in_keyring and not Flags.is_set((Flags.ignore_keys_not_in_keyring,), *flags) and not resource.mode_properties.read_only:
            raise ValueError(f"Some keys in the resource were not in the keyring: {_keys_not_in_keyring}\n"
                             f"You can set to ignore this through the flag {Flags.ignore_keys_not_in_keyring}, "
                             f"or by setting the resource's mode property to one that includes 'read_only'")
        elif _keys_not_in_keyring and Flags.is_set((Flags.ignore_keys_not_in_keyring,), *flags):
            warnings.warn(f"Keys were found in the resource '{resource}' that are not in the keyring, "
                          f"but you have set to ignore keys found that are not in the keyring. "
                          f"These ignored keys will not be loaded to the vault.\n"
                          f"Keys not in the keyring: {_keys_not_in_keyring}")
        initial_vars = resource.create_mv(**keys_in_keyring)

    vault = VarVault(*flags,
                     keyring=keyring,
                     name=name,
                     resource=resource,
                     logger=logger,
                     initial_vars=initial_vars,
                     **extra_keys)

    return vault