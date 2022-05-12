from .filehandlers import JsonFilehandler

from .keyring import Key, Keyring, validator

from .minivault import MiniVault

from .utils import *

from .vault import VarVault, VarVaultInterface

from .vaultflags import VaultFlags

from .vaultfactory import create_vault
from .vaultfactory import from_vault

from .vaultstructs import *


class FileTypes:
    JSON: Type[JsonFilehandler] = JsonFilehandler


def clear_logs():
    import os
    import glob
    import tempfile

    path = os.path.join(tempfile.tempdir, "varvault-logs", "*.log")
    files = glob.glob(path)
    for f in files:
        os.remove(f)
