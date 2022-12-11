import logging
import warnings

from typing import Type

from .resource import BaseResource
from .keyring import Keyring, Key
from .flags import Flags
from .vault import VarVault


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
