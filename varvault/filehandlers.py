import abc
import json
import os.path
import threading
import warnings

from typing import Union, Dict, List, TextIO


class BaseFileHandler(abc.ABC):
    def __init__(self, filename: str, live_update=False, file_is_read_only=False):
        self.lock = threading.Lock()
        self.raw_filename = filename
        self.live_update = live_update
        self.file_is_read_only = file_is_read_only
        self.file = filename

    @property
    def file(self) -> TextIO:
        return self.file_io

    @file.setter
    def file(self, filename: str):

        if filename and self.live_update and not os.path.exists(filename):
            self.file_io = None
            raise FileNotFoundError("Unable to find the file and live-update is defined. This is fine, but we need to raise the error and handle it.")
        elif filename and not os.path.exists(filename):
            # Create the file; It doesn't exist
            self.file_io = open(filename, "w")
            self.file_io.close()
        elif filename and os.path.exists(filename):
            # The file already exists; Just read from it
            self.file_io = open(filename)
            self.file_io.close()
        else:
            raise NotImplementedError("This is not supported")

    # ================================================================================================================
    # Write
    # ================================================================================================================
    def write(self, vault: dict):
        if self.file_is_read_only:
            warnings.warn("Tried to write to a vault-file defined as read-only. This is not permitted by varvault.")
        if self.file:
            with self.lock:
                self.do_write(vault)

    @abc.abstractmethod
    def do_write(self, vault: dict):
        """
        A function to write data to a file. Varvault will call this function internally.
        The class that implements this abstractmethod has to write a dict to a file and then close the file.

        Example:
        `json.dump(vault, open(self.file.name, "w"), indent=2)`

        :param vault: The vault to write to the file.
        :return: None. Varvault will not use the return value from this function
        """
        pass

    # ================================================================================================================
    # Read
    # ================================================================================================================
    def read(self) -> Dict:
        if self.file:
            with self.lock:
                try:
                    return self.do_read()
                except Exception as e:
                    if self.live_update:
                        # live-update has been defined; This means that any error from reading
                        # the file must be considered okay as the file might not exist yet.
                        return {}
                    raise e

    @abc.abstractmethod
    def do_read(self) -> Dict:
        """
        A function to read data from a file. Varvault will call this function internally.
        The class that implements this abstractmethod has to read data from a file and then return it.

        Example:
        `return json.load(open(self.file.name))`

        :return: A dict describing the vault from the file.
        """
        pass


class JsonFilehandler(BaseFileHandler):
    def __init__(self, filename: str, live_update=False, file_is_read_only=False):
        super(JsonFilehandler, self).__init__(filename, live_update, file_is_read_only)

    def do_write(self, vault: dict):
        json.dump(vault, open(self.file.name, "w"), indent=2)

    def do_read(self) -> Union[Dict, List]:
        return json.load(open(self.file.name))
