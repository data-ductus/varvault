import json
import logging
import os

from typing import *

from .keyring import Keyring
from .vaultflags import VaultFlags
from .vault import VarVault
from .utils import create_return_vault_from_file


def create_vault(keyring: Type[Keyring],
                 vault_name: str,
                 *flags: VaultFlags,
                 vault_filename_to: str = None,
                 use_logger: bool = True,
                 specific_logger: logging.Logger = None,
                 **extra_keys) -> VarVault:
    """
    Factory-function to help create a Vault-object instead of creating it manually (which is still possible).

    :param keyring: Describes which keys belong to this Vault.
    :param vault_name: Used to name the vault and the logger for writing information and debug messages.
    :param vault_filename_to: Optional filename for a .JSON file to write the arguments in the vault to.
    :param use_logger: Optional argument for telling varvault to use a logger or not. Default behavior is to use a logger object.
    :param flags: Optional argument for defining VaultFlags for this Vault.
     Note that any global VaultFlag will be overridden by VaultFlags defined in a vault-decorator.
    :param specific_logger: Optional argument for defining your own logger object if you want to use a specific logger rather than varvault's own logger.
    :param extra_keys: Extra keys as a dict to write to. These keys can be defined during runtime, which can sometimes be necessary.
     It is recommended to use pre-determined keys (e.g. constants), but sometimes being more flexible can be useful.
    :return: Vault object based on input to this function.
    """
    return VarVault(keyring, vault_name, *flags, vault_filename_from=vault_filename_to, vault_filename_to=vault_filename_to, remove_existing_log_file=True, use_logger=use_logger, specific_logger=specific_logger, **extra_keys)


def from_vault(keyring: Type[Keyring],
               vault_name: str,
               vault_filename_from: str,
               *flags: VaultFlags,
               vault_filename_to: str = None,
               file_is_read_only: bool = False,
               use_logger: bool = True,
               ignore_keys_not_in_keyring: bool = False,
               remove_existing_log_file: bool = False,
               specific_logger: logging.Logger = None,
               **extra_keys) -> VarVault:
    """
    Factory-function to help create a Vault-object from an existing vault file.

    :param keyring: Describes which keys belong to this Vault.
    :param vault_name: Used to name the vault and the logger for writing information and debug messages.
    :param vault_filename_from: Filename for a .JSON file to load variables from.
    :param flags: A set of VaultFlags to tweak the behavior of the vault.
    :param vault_filename_to: Optional filename to write the variables to. This can be a separate file to the file we read from.
    :param file_is_read_only: Optional argument to say that the file we read from is read-only so that no writes to the file can be done.
     You are still allowed to put new things in the vault, but nothing will be written to the file.
    :param use_logger: Optional argument for telling varvault to use a logger or not. Default behavior is to use a logger object.
    :param specific_logger: Optional argument for defining your own logger object if you want to use a specific logger rather than varvault's own logger.
    :param remove_existing_log_file: Optional argument for deleting an existing log file. Default is to not remove an existing log file.
    :param ignore_keys_not_in_keyring: Optional argument to ignore keys not in the keyring when loading a vault from the file that has keys that doesn't match.
    This can be useful when changing the keyring without it being a real issue.
    :param extra_keys: Extra keys as a dict to write to. These keys can be defined during runtime, which can sometimes be necessary.
    It is recommended to use pre-determined keys (e.g. constants), but sometimes being more flexible can be useful.
    :return: A vault based on vault_filename_from and keyring.
    """
    vault_filename_from = os.path.expanduser(os.path.expandvars(vault_filename_from))

    if not os.path.exists(vault_filename_from) and not VaultFlags.flag_is_set(VaultFlags.live_update(), *flags):
        raise FileNotFoundError(f"Vault-file {vault_filename_from} doesn't appear to exist, and you have not requested live-update via the flag {VaultFlags.live_update.__name__}.")

    if vault_filename_to:
        vault_filename_to = os.path.expanduser(os.path.expandvars(vault_filename_to))
    else:
        vault_filename_to = vault_filename_from

    def _check_for_keys_not_in_keyring():
        try:
            vault_file_data = json.load(open(vault_filename_from))
        except FileNotFoundError:
            if VaultFlags.flag_is_set(VaultFlags.live_update(), *flags):
                # No point checking for keys not in the keyring at this point
                return list()
            else:
                raise

        assert isinstance(vault_file_data, dict), f"It appears we were not able to load a JSON from {vault_filename_from}. Are you sure this is a valid JSON?"
        keys_in_keyring = keyring.get_keys_in_keyring()
        keys_in_keyring.update(extra_keys)
        keys_in_file = vault_file_data.keys()
        _keys_not_in_keyring = [k for k in keys_in_file if k not in keys_in_keyring]
        assert len(_keys_not_in_keyring) == 0 or ignore_keys_not_in_keyring, f"Keys found in vault-file '{vault_filename_from}' that are not in the keyring, " \
                                                                             f"and you have not set to ignore keys found that are not in the keyring. " \
                                                                             f"Keys not in keyring: {_keys_not_in_keyring}"
        return _keys_not_in_keyring
    keys_not_in_keyring = _check_for_keys_not_in_keyring()

    mini = create_return_vault_from_file(vault_filename_from, keyring, live_update=VaultFlags.flag_is_set(VaultFlags.live_update(), *flags), **extra_keys)

    vault = VarVault(keyring, vault_name, *flags,
                     use_logger=use_logger,
                     vault_filename_from=vault_filename_from,
                     vault_filename_to=vault_filename_to,
                     file_is_read_only=file_is_read_only,
                     remove_existing_log_file=remove_existing_log_file,
                     specific_logger=specific_logger,
                     **extra_keys)
    vault.vault.put(mini)

    if len(keys_not_in_keyring) and ignore_keys_not_in_keyring:
        vault.log(f"Vault was created from file '{vault_filename_from}', and the file contained keys not in the keyring ({keys_not_in_keyring}), "
                  f"but you asked to ignore if this happens through setting 'ignore_keys_not_in_keyring' to True.", level=logging.WARNING)
    else:
        vault.log(f"Vault created from file '{vault_filename_from}'.", level=logging.INFO)

    return vault
