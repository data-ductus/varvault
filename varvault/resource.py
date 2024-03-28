from __future__ import annotations

import abc
import enum
import os.path
import warnings
import threading

from typing import Union, Dict, Any, AnyStr, Literal

from .keyring import Key
from .minivault import MiniVault
from .vaultstructs import VaultStructBase
from .utils import assert_and_raise
from .threadgroup import threaded_execution, create_functions


class ModeProperties(dict):
    def __setattr__(self, key, value):
        if hasattr(self, "initialized") and self.initialized:
            raise AttributeError("ModeProperties are immutable")
        super(ModeProperties, self).__setattr__(key, value)
        super(ModeProperties, self).__setitem__(key, value)

    def __init__(self, read_only: bool, live_update: bool, create: bool, load: bool, write: bool, create_func: callable):
        self.initialized = False
        super().__init__()
        self.read_only = read_only
        self.live_update = live_update
        self.create = create
        self.load = load
        self.write = write
        self.create_func = create_func
        self.initialized = True


class ResourceModes(enum.Enum):
    READ = "r"                     # Read from existing resource (default)
    WRITE = "w"                    # Create new resource and ignore existing resource and write to it
    APPEND = "a"                   # Create a new resource if none exist, otherwise read from and write to existing resource
    READ_W_LIVE_UPDATE = "r+"      # Read from existing resource and perform live-update
    WRITE_W_LIVE_UPDATE = "w+"     # Create new resource and ignore existing resource and write to it, and perform live-update
    APPEND_W_LIVE_UPDATE = "a+"    # Create a new resource if none exist, otherwise read from and write to existing resource, and perform live-update


class BaseResource(abc.ABC):

    POSSIBLE_MODES = {
        ResourceModes.READ.value,
        ResourceModes.WRITE.value,
        ResourceModes.APPEND.value,
        ResourceModes.READ_W_LIVE_UPDATE.value,
        ResourceModes.WRITE_W_LIVE_UPDATE.value,
        ResourceModes.APPEND_W_LIVE_UPDATE.value,
    }

    @abc.abstractmethod
    def read_mode(self):
        """Meant to create the resource when read-mode is selected"""
        pass

    @abc.abstractmethod
    def write_mode(self):
        """Meant to crete the resource when write-mode is selected"""
        pass

    @abc.abstractmethod
    def append_mode(self):
        """Meant to crete the resource when append-mode is selected"""
        pass

    @abc.abstractmethod
    def read_live_update_mode(self):
        """Meant to crete the resource when read-with-live-update-mode is selected"""
        pass

    @abc.abstractmethod
    def write_live_update_mode(self):
        """Meant to crete the resource when write-with-live-update-mode is selected"""
        pass

    @abc.abstractmethod
    def append_live_update_mode(self):
        """Meant to crete the resource when append-with-live-update-mode is selected"""
        pass

    MODE_MAPPING: Dict[str, ModeProperties] = {
        ResourceModes.READ.value:                  ModeProperties(read_only=True,  live_update=False, create=False, load=True,  write=False, create_func=read_mode),
        ResourceModes.WRITE.value:                 ModeProperties(read_only=False, live_update=False, create=True,  load=False, write=True,  create_func=write_mode),
        ResourceModes.APPEND.value:                ModeProperties(read_only=False, live_update=False, create=True,  load=True,  write=True,  create_func=append_mode),
        ResourceModes.READ_W_LIVE_UPDATE.value:    ModeProperties(read_only=True,  live_update=True,  create=False, load=True,  write=False, create_func=read_live_update_mode),
        ResourceModes.WRITE_W_LIVE_UPDATE.value:   ModeProperties(read_only=False, live_update=True,  create=True,  load=False, write=True,  create_func=write_live_update_mode),
        ResourceModes.APPEND_W_LIVE_UPDATE.value:  ModeProperties(read_only=False, live_update=True,  create=True,  load=True,  write=True,  create_func=append_live_update_mode)
    }

    def __init__(self, path: Union[AnyStr, Any], mode: Union[Literal["r", "w", "a", "r+", "w+", "a+"], ResourceModes] = "r"):
        """
        Creates an object that can be used to read and write to a resource.

        :param path: This is the path to the resource. It can be essentially anything that identifies it. Any resource has a path to where it is located.
        :param mode: Sets the mode of the resource. The mode can be one of the following: 'r', 'w', 'a', 'r+', 'w+', 'a+'.
        r: Read from existing resource (default)
        w: Create new resource and ignore existing resource and write to it
        a: Create a new resource if none exist, otherwise read from and write to existing resource
        r+: Read from existing resource and perform live-update
        w+: Create new resource and ignore existing resource and write to it, and perform live-update
        a+: Create a new resource if none exist, otherwise read from and write to existing resource, and perform live-update

        """
        self.lock = threading.Lock()

        if isinstance(mode, ResourceModes):
            mode = mode.value
        self.mode = mode
        assert_and_raise(self.mode in self.POSSIBLE_MODES, ValueError(f"Invalid mode: {self.mode}. Must be one of the following: {self.POSSIBLE_MODES}"))
        if self.mode not in self.POSSIBLE_MODES:
            raise ValueError(f"Invalid mode: {self.mode}. Must be one of the following: {self.POSSIBLE_MODES}")

        self.raw_path = os.path.expanduser(os.path.expandvars(path))

        self.mode_properties: ModeProperties = self.MODE_MAPPING[self.mode]
        self.last_known_state = None
        self.cached_state = None
        if self.mode_properties.load and not self.mode_properties.create and not self.exists() and not self.mode_properties.live_update:
            raise ResourceNotFoundError(f"Resource not found at: {self.raw_path} (mode is {self.mode})", self)

    def resource_has_changed(self):
        """Returns a bool that says if the resource has changed since the last time it was read."""
        self.last_known_state = self.state
        return self.cached_state != self.last_known_state

    def update_state(self, fetch_state=True):
        """Updates the state by fetching the current state."""
        if fetch_state:
            self.last_known_state = self.state
        self.cached_state = self.last_known_state

    def create_mv(self, **keys: Key) -> MiniVault:
        f"""Creates a {MiniVault}-object from a file by loading the vault from the file using the keyring."""

        vault_file_data = self.read()

        assert isinstance(vault_file_data, dict), f"'vault_file_data' from the filehandler is not a dict: {vault_file_data}"

        # Get the keys from the keyring as a list.
        return_vault_data = dict()

        def build(key_in_file: str):
            if key_in_file not in keys:
                return
            key: Key = keys[key_in_file]
            if key.valid_type and issubclass(key.valid_type, VaultStructBase):
                return_vault_data[key] = key.valid_type.create(key_in_file, vault_file_data[key_in_file])
            else:
                if key.can_be_none and vault_file_data[key_in_file] is None:
                    return_vault_data[key] = None
                else:
                    assert key.valid_type is None or isinstance(vault_file_data[key_in_file], key.valid_type), f"Key type missmatch ({key}; Valid type {key.valid_type}, actual type: {type(vault_file_data[key_in_file])}"
                    return_vault_data[key] = vault_file_data[key_in_file]

        threaded_execution(create_functions(build, vault_file_data.keys()))

        return MiniVault(**return_vault_data)

    def create(self):
        getattr(self, self.mode_properties.create_func.__name__)()

    @property
    @abc.abstractmethod
    def resource(self) -> Any:
        """Meant to return the resource that stores the vault in some database such as a file."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def state(self):
        """Meant to return the state of the resource, such as a hash of the resource."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def path(self) -> Union[AnyStr, Any]:
        """Meant to return the path to the database that stores the vault."""
        raise NotImplementedError()

    @abc.abstractmethod
    def writable(self, obj: Dict) -> bool:
        """Meant to return a bool that says if a given key-value pair in a dict can be successfully written to the database."""
        raise NotImplementedError()

    @abc.abstractmethod
    def exists(self) -> bool:
        """Meant to return a bool which says if the resource exists or not"""
        raise NotImplementedError()

    # ================================================================================================================
    # Write
    # ================================================================================================================
    def write(self, vault: dict) -> None:
        f"""Writes the vault to the database by calling the implemented '{self.do_write}' method. Not meant to be overridden."""
        if not vault:
            # No point writing an empty dict and it's not the job of this method to create the file
            return

        if self.mode_properties.read_only:
            warnings.warn("Tried to write to a resource defined as read-only. This is not permitted by varvault.")
            return

        if not self.resource:
            self.create()
        try:
            with self.lock:
                self.do_write(vault)
        except Exception as e:
            raise ResourceNotFoundError(f"Failed to write to the resource: {e}", self)
        self.update_state()

    @abc.abstractmethod
    def do_write(self, vault: dict) -> None:
        """
        A function to write a vault to a file/database. Varvault will call this function internally.
        The class that implements this abstract method has to write a dict to a resource.

        Example:

        ``json.dump(vault, open(self.path, "w"), indent=2)``

        :param vault: The vault to write to the file.
        :return: None. Varvault will not use the return value from this function
        """
        raise NotImplementedError()

    # ================================================================================================================
    # Read
    # ================================================================================================================
    def read(self) -> Dict:
        f"""Reads the vault from the database by calling the implemented '{self.do_read}' method. Not meant to be overridden."""
        if not self.resource:
            self.create()
        with self.lock:
            if self.exists():
                try:
                    data = self.do_read()
                    self.update_state()
                    return data
                except Exception as e:
                    raise ResourceNotFoundError(f"Failed to read from the resource (mode is {self.mode}): {e}", self)
            if self.mode_properties.live_update:
                return {}
            raise ResourceNotFoundError(f"Resource not found at: {self.raw_path} (mode is {self.mode})", self)

    @abc.abstractmethod
    def do_read(self) -> Dict:
        """
        A function to read data from a file/database. Varvault will call this function internally.
        The class that implements this abstractmethod has to read data from a file and then return it.

        Example:

        ``return json.load(open(self.path))``

        :return: A dict describing the vault from the resource.
        """
        raise NotImplementedError()

    def __str__(self):
        return f"resource={self.resource}; path={self.path}; live_update={self.mode_properties.live_update}; vault_is_read_only={self.mode_properties.read_only}"


class ResourceNotFoundError(FileNotFoundError):
    def __init__(self, msg, resource: BaseResource):
        super(ResourceNotFoundError, self).__init__(msg)
        self.msg = msg
        self.resource = resource

    def __repr__(self):
        return f"ResourceNotFoundError: {self.msg}; {self.resource.mode_properties}"

    def __str__(self):
        return f"{self.msg} - {self.resource.mode_properties}"
