from .keyring import Key, Keyring

from .minivault import MiniVault

from .utils import *

from .vault import VarVault

from .vaultflags import VaultFlags

from .vaultfactory import create_vault
from .vaultfactory import from_vault

from .vaultstructs import *


def clear_logs():
    import os
    import glob

    files = glob.glob("/tmp/varvault-logs/*.log")
    for f in files:
        os.remove(f)
