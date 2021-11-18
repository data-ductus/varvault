import json
import logging
import os

from typing import *

from . import MiniVault
from .keyring import Keyring
from .vaultflags import VaultFlags
from .vault import VarVault
from .utils import create_mini_vault_from_file


def create_vault(varvault_keyring: Type[Keyring],
                 varvault_vault_name: str,
                 *flags: VaultFlags,
                 varvault_vault_filename_to: str = None,
                 varvault_specific_logger: logging.Logger = None,
                 **extra_keys) -> VarVault:
    """
    Factory-function to help create a Vault-object instead of creating it manually (which is still possible).

    :param varvault_keyring: Describes which keys belong to this Vault.
    :param varvault_vault_name: Used to name the vault and the logger for writing information and debug messages.
    :param varvault_vault_filename_to: Optional filename for a .JSON file to write the arguments in the vault to.
    :param use_logger: Optional argument for telling varvault to use a logger or not. Default behavior is to use a logger object.
    :param flags: Optional argument for defining VaultFlags for this Vault.
     Note that any global VaultFlag will be overridden by VaultFlags defined in a vault-decorator.
    :param varvault_specific_logger: Optional argument for defining your own logger object if you want to use a specific logger rather than varvault's own logger.
    :param extra_keys: Extra keys as a dict to write to. These keys can be defined during runtime, which can sometimes be necessary.
     It is recommended to use pre-determined keys (e.g. constants), but sometimes being more flexible can be useful.
    :return: Vault object based on input to this function.
    """
    if not VaultFlags.flag_is_set(VaultFlags.remove_existing_log_file(), *flags):
        flags = (VaultFlags.remove_existing_log_file(), *flags)
    return VarVault(varvault_keyring, varvault_vault_name, *flags, varvault_vault_filename_from=varvault_vault_filename_to, varvault_vault_filename_to=varvault_vault_filename_to, varvault_specific_logger=varvault_specific_logger, **extra_keys)


def from_vault(varvault_keyring: Type[Keyring],
               varvault_vault_name: str,
               varvault_vault_filename_from: str,
               *flags: VaultFlags,
               varvault_vault_filename_to: str = None,
               varvault_specific_logger: logging.Logger = None,
               **extra_keys) -> VarVault:
    """
    Factory-function to help create a Vault-object from an existing vault file.

    :param varvault_keyring: Describes which keys belong to this Vault.
    :param varvault_vault_name: Used to name the vault and the logger for writing information and debug messages.
    :param varvault_vault_filename_from: Filename for a .JSON file to load variables from.
    :param flags: A set of VaultFlags to tweak the behavior of the vault.
    :param varvault_vault_filename_to: Optional filename to write the variables to. This can be a separate file to the file we read from.
    :param varvault_specific_logger: Optional argument for defining your own logger object if you want to use a specific logger rather than varvault's own logger.
    This can be useful when changing the keyring without it being a real issue.
    :param extra_keys: Extra keys as a dict to write to. These keys can be defined during runtime, which can sometimes be necessary.
    It is recommended to use pre-determined keys (e.g. constants), but sometimes being more flexible can be useful.
    :return: A vault based on vault_filename_from and keyring.
    """
    varvault_vault_filename_from = os.path.expanduser(os.path.expandvars(varvault_vault_filename_from))
    live_update = VaultFlags.flag_is_set(VaultFlags.live_update(), *flags)
    ignore_keys_not_in_keyring = VaultFlags.flag_is_set(VaultFlags.file_is_read_only(), *flags) or VaultFlags.flag_is_set(VaultFlags.ignore_keys_not_in_keyring(), *flags)

    if not os.path.exists(varvault_vault_filename_from) and not live_update:
        raise FileNotFoundError(f"Vault-file {varvault_vault_filename_from} doesn't appear to exist, and you have not requested live-update via the flag {VaultFlags.live_update.__name__}.")

    if varvault_vault_filename_to:
        varvault_vault_filename_to = os.path.expanduser(os.path.expandvars(varvault_vault_filename_to))
    else:
        varvault_vault_filename_to = varvault_vault_filename_from

    def _check_for_keys_not_in_keyring():
        try:
            vault_file_data = json.load(open(varvault_vault_filename_from))
        except FileNotFoundError:
            if VaultFlags.flag_is_set(VaultFlags.live_update(), *flags):
                # No point checking for keys not in the keyring at this point
                return list()
            else:
                raise

        assert isinstance(vault_file_data, dict), f"It appears we were not able to load a JSON from {varvault_vault_filename_from}. Are you sure this is a valid JSON?"
        keys_in_keyring = varvault_keyring.get_keys_in_keyring()
        keys_in_keyring.update(extra_keys)
        keys_in_file = vault_file_data.keys()
        _keys_not_in_keyring = [k for k in keys_in_file if k not in keys_in_keyring]
        assert len(_keys_not_in_keyring) == 0 or ignore_keys_not_in_keyring, \
            f"Keys found in vault-file '{varvault_vault_filename_from}' that are not in the keyring, " \
            f"and you have not set to ignore keys found that are not in the keyring. " \
            f"Keys not in keyring: {_keys_not_in_keyring}"

        return _keys_not_in_keyring
    keys_not_in_keyring = _check_for_keys_not_in_keyring()
    try:
        mini = create_mini_vault_from_file(varvault_vault_filename_from, varvault_keyring, **extra_keys)
    except FileNotFoundError:
        if live_update:
            # This is fine; If live_update is defined, it must be possible for the file to not exist yet.
            mini = MiniVault()
        else:
            raise

    vault = VarVault(varvault_keyring, varvault_vault_name, *flags,
                     varvault_vault_filename_from=varvault_vault_filename_from,
                     varvault_vault_filename_to=varvault_vault_filename_to,
                     varvault_specific_logger=varvault_specific_logger,
                     **extra_keys)
    vault.vault.put(mini)

    if len(keys_not_in_keyring) and ignore_keys_not_in_keyring:
        vault.log(f"Vault was created from file '{varvault_vault_filename_from}', and the file contained keys not in the keyring ({keys_not_in_keyring}), "
                  f"but you asked to ignore if this happens through setting 'ignore_keys_not_in_keyring' to True.", level=logging.WARNING)
    else:
        vault.log(f"Vault created from file '{varvault_vault_filename_from}'.", level=logging.INFO)

    return vault
