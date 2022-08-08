import abc
import os.path
import warnings
import threading

from typing import Union, Dict, Any, AnyStr


class BaseFileHandler(abc.ABC):
    def __init__(self, path: Union[AnyStr, Any], live_update=False, vault_is_read_only=False):
        self.lock = threading.Lock()
        self.raw_path = os.path.expanduser(os.path.expandvars(path))
        self.live_update = live_update
        self.vault_is_read_only = vault_is_read_only

    @property
    def live_update(self):
        return self._live_update

    @live_update.setter
    def live_update(self, v: bool):
        assert isinstance(v, bool), f"Value must be a {bool}"
        self._live_update = v

    @property
    def vault_is_read_only(self):
        return self._vault_is_read_only

    @vault_is_read_only.setter
    def vault_is_read_only(self, v: bool):
        assert isinstance(v, bool), f"Value must be a {bool}"
        self._vault_is_read_only = v

    @property
    @abc.abstractmethod
    def resource(self) -> Any:
        """Meant to return the resource that stores the vault in some database."""
        raise NotImplementedError()

    # TODO 4.0.0: remove path as an argument from this and expect the subclass to handle this bit
    @abc.abstractmethod
    def create_resource(self, path: Union[AnyStr, Any]):
        """Meant to create the resource to store the vault in a database."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def path(self) -> Union[AnyStr, Any]:
        """Meant to return the path to the database that stores the vault."""
        raise NotImplementedError()

    @abc.abstractmethod
    def kv_pair_can_be_written(self, obj: Dict) -> bool:
        """Meant to return a bool that says if a given key-value pair can be successfully written to the database."""
        raise NotImplementedError()

    @abc.abstractmethod
    def hash(self) -> str:
        """Meant to return a hash for the database so varvault knows if the vault that is loaded in memory is different from the vault in the file/database."""
        raise NotImplementedError()

    @abc.abstractmethod
    def exists(self) -> bool:
        """Meant to return a bool which says if the resource exists or not"""
        raise NotImplementedError()

    # ================================================================================================================
    # Write
    # ================================================================================================================
    def write(self, vault: dict) -> None:
        f"""Writes the vault to the database by calling the implemented '{self.do_write}' method."""
        if not vault:
            # No point writing an empty dict and it's not the job of this method to create the file
            return
        if self._vault_is_read_only:
            warnings.warn("Tried to write to a vault-file defined as read-only. This is not permitted by varvault.")
        if not self.resource:
            self.create_resource(self.path)
        try:
            with self.lock:
                self.do_write(vault)
        except Exception as e:
            raise ResourceNotFoundError(f"Failed to write to the resource: {e}", self)

    @abc.abstractmethod
    def do_write(self, vault: dict) -> None:
        """
        A function to write a vault to a file/database. Varvault will call this function internally.
        The class that implements this abstract method has to write a dict to a resource.

        Example:
        `json.dump(vault, open(self.path, "w"), indent=2)`

        :param vault: The vault to write to the file.
        :return: None. Varvault will not use the return value from this function
        """
        raise NotImplementedError()

    # ================================================================================================================
    # Read
    # ================================================================================================================
    def read(self) -> Dict:
        f"""Reads the vault from the database by calling the implemented '{self.do_read}' method."""
        if not self.resource:
            self.create_resource(self.path)
        try:
            with self.lock:
                return self.do_read()
        except Exception as e:
            if self.live_update:
                # live-update has been defined; This means that any error from reading
                # the file must be considered okay as the file might not exist yet.
                return {}
            raise ResourceNotFoundError(f"Failed to read from the resource and live-update isn't defined: {e}", self)

    @abc.abstractmethod
    def do_read(self) -> Dict:
        """
        A function to read data from a file/database. Varvault will call this function internally.
        The class that implements this abstractmethod has to read data from a file and then return it.

        Example:
        `return json.load(open(self.path))`

        :return: A dict describing the vault from the file.
        """
        raise NotImplementedError()

    def __str__(self):
        return f"resource={self.resource}; path={self.path}; live_update={self.live_update}; vault_is_read_only={self._vault_is_read_only}"


class ResourceNotFoundError(FileNotFoundError):
    def __init__(self, msg, filehandler: BaseFileHandler):
        super(ResourceNotFoundError, self).__init__(msg)
        self.msg = msg
        self.filehandler = filehandler

    def __str__(self):
        return f"{self.msg} - {self.filehandler}"
