import logging

from typing import Type

from .filehandlers import BaseFileHandler, ResourceNotFoundError
from .keyring import Keyring
from .minivault import MiniVault
from .vaultflags import VaultFlags
from .vault import VarVault
from .utils import create_mv_from_resource


def create_vault(varvault_keyring: Type[Keyring],
                 varvault_vault_name: str,
                 *flags: VaultFlags,
                 varvault_filehandler_to: BaseFileHandler = None,
                 varvault_specific_logger: logging.Logger = None,
                 **extra_keys) -> VarVault:
    """
    Factory-function to help create a Vault-object instead of creating it manually (which is still possible).

    :param varvault_keyring: Describes which keys belong to this Vault.
    :param varvault_vault_name: Used to name the vault and the logger for writing information and debug messages.
    :param varvault_filehandler_to: Optional filehandler for a file to write the arguments in the vault to.
    :param flags: Optional argument for defining VaultFlags for this Vault.
     Note that any global VaultFlag will be overridden by VaultFlags defined in a vault-decorator.
    :param varvault_specific_logger: Optional argument for defining your own logger object if you want to use a specific logger rather than varvault's own logger.
    :param extra_keys: Extra keys as a dict to write to. These keys can be defined during runtime, which can sometimes be necessary.
     It is recommended to use pre-determined keys (e.g. constants), but sometimes being more flexible can be useful.
    :return: Vault object based on input to this function.
    """
    if not VaultFlags.flag_is_set(VaultFlags.remove_existing_log_file(), *flags):
        flags = (VaultFlags.remove_existing_log_file(), *flags)
    if varvault_filehandler_to:
        varvault_filehandler_to.live_update = VaultFlags.flag_is_set(VaultFlags.live_update(), *flags)
    return VarVault(varvault_keyring, varvault_vault_name, *flags,
                    varvault_filehandler_from=varvault_filehandler_to,
                    varvault_filehandler_to=varvault_filehandler_to,
                    varvault_specific_logger=varvault_specific_logger,
                    **extra_keys)


def from_vault(varvault_keyring: Type[Keyring],
               varvault_vault_name: str,
               varvault_filehandler_from: BaseFileHandler,
               *flags: VaultFlags,
               varvault_filehandler_to: BaseFileHandler = None,
               varvault_specific_logger: logging.Logger = None,
               **extra_keys) -> VarVault:
    """
    Factory-function to help create a Vault-object from an existing vault file.

    :param varvault_keyring: Describes which keys belong to this Vault.
    :param varvault_vault_name: Used to name the vault and the logger for writing information and debug messages.
    :param varvault_filehandler_from: Filehandler for a file to load variables from.
    :param flags: A set of VaultFlags to tweak the behavior of the vault.
    :param varvault_filehandler_to: Optional filehandler to write the variables to. This can be a separate file to the file we read from. If left as None, this will be set to 'varvault_filehandler_from'.
    :param varvault_specific_logger: Optional argument for defining your own logger object if you want to use a specific logger rather than varvault's own logger.
    This can be useful when changing the keyring without it being a real issue.
    :param extra_keys: Extra keys as a dict to write to. These keys can be defined during runtime, which can sometimes be necessary.
    It is recommended to use pre-determined keys (e.g. constants), but sometimes being more flexible can be useful.
    :return: A vault based on vault_filename_from and keyring.
    """
    ignore_keys_not_in_keyring = VaultFlags.flag_is_set(VaultFlags.vault_is_read_only(), *flags) or VaultFlags.flag_is_set(VaultFlags.ignore_keys_not_in_keyring(), *flags)
    varvault_filehandler_from.live_update = VaultFlags.flag_is_set(VaultFlags.live_update(), *flags)
    varvault_filehandler_from.vault_is_read_only = VaultFlags.flag_is_set(VaultFlags.vault_is_read_only(), *flags)

    if not varvault_filehandler_to:
        varvault_filehandler_to = varvault_filehandler_from

    keys_not_in_keyring = _check_for_keys_not_in_keyring(varvault_keyring, varvault_filehandler_from, ignore_keys_not_in_keyring, **extra_keys)
    if varvault_filehandler_from.exists():
        mini = create_mv_from_resource(varvault_filehandler_from, varvault_keyring, **extra_keys)
    elif not varvault_filehandler_from.exists() and VaultFlags.flag_is_set(VaultFlags.live_update(), *flags):
        mini = MiniVault()
    else:
        raise ResourceNotFoundError(f"The resource to load the vault from doesn't exist and live-update is not defined", varvault_filehandler_from)

    vault = VarVault(varvault_keyring, varvault_vault_name, *flags,
                     varvault_filehandler_from=varvault_filehandler_from,
                     varvault_filehandler_to=varvault_filehandler_to,
                     varvault_specific_logger=varvault_specific_logger,
                     **extra_keys)
    vault.vault.put(mini)

    if len(keys_not_in_keyring) and ignore_keys_not_in_keyring:
        vault.log(f"Vault was created from file '{varvault_filehandler_from.path}', and the file contained keys not in the keyring ({keys_not_in_keyring}), "
                  f"but you asked to ignore if this happens through setting 'ignore_keys_not_in_keyring' to True.", level=logging.WARNING)
    else:
        vault.log(f"Vault created from file '{varvault_filehandler_from.path}'.", level=logging.INFO)

    return vault


def _check_for_keys_not_in_keyring(varvault_keyring: Type[Keyring], varvault_filehandler_from: BaseFileHandler, ignore_keys_not_in_keyring: bool, **extra_keys):
    vault_file_data = varvault_filehandler_from.read()

    assert isinstance(vault_file_data, dict), f"It appears we were not able to load a Dict from {varvault_filehandler_from}. Are you sure this is a valid resource? (content={vault_file_data})"
    keys_in_keyring = varvault_keyring.get_keys()
    keys_in_keyring.update(extra_keys)
    keys_in_file = vault_file_data.keys()
    _keys_not_in_keyring = [k for k in keys_in_file if k not in keys_in_keyring]
    assert len(_keys_not_in_keyring) == 0 or ignore_keys_not_in_keyring, \
        f"Keys found in vault-path '{varvault_filehandler_from}' that are not in the keyring, " \
        f"and you have not set to ignore keys found that are not in the keyring. " \
        f"Keys not in keyring: {_keys_not_in_keyring}"

    return _keys_not_in_keyring
