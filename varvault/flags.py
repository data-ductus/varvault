from __future__ import annotations

import enum
from typing import Tuple, Union


class Flags(enum.Enum):
    @staticmethod
    def is_set(flag: Union[Flags, Tuple], *flags: Flags):
        f"""This is not a flag. This function checks if a flag exists among a bunch of flags"""
        if isinstance(flag, tuple):
            return any([f in flags for f in flag])
        return flag in flags

    f"""Flag to set if return values must be something other than {None}. By default, this is fine, but you can enforce return variables to be something other than {None}"""
    return_values_cannot_be_none = enum.auto()

    f"""Flag to set if variables may be modified either in the vault itself or for a specific decorated function. 
        By default, varvault doesn't permit modifications to existing keys as this can cause unintended behavior."""
    permit_modifications = enum.auto()

    f"""Flag to set if an input variable may be missing in a vault when it is accessed. In this case, the key will be sent to kwargs but it will be mapped to {None}."""
    input_key_can_be_missing = enum.auto()

    f"""Flag to clean return keys in a vault defined for a decorated function. This can be used during a cleanup stage. 
    Varvault will try to map the key to a default value for the valid type, like for example str(), or list(). If it doesn't work, the key will be mapped to {None}."""
    clean_return_keys = enum.auto()

    f"""Flag to enable debug mode for logger output to the console to help you with debugging. By default, varvault will write debug logs to the logfile, but not the console. 
    By setting this, you'll have a much easier time debugging unintended behavior. Using this and 'silent' (see further down) in conjunction will cancel each other out and make logging the default."""
    debug = enum.auto()

    f"""Flag to enable silent mode for a vault. This will completely remove debug logs being written to the logfile. This can be used to reduce unnecessary
         bloat and make debugging much more easy to do. Using this and {debug} in conjunction will cancel each other out and make logging the default."""
    silent = enum.auto()

    f"""Flag to tell varvault that the return value is a tuple that should be mapped to a single return-key. Varvault cannot tell if 
    a tuple is multiple return values or a single item meant for a single key as this how Python handles multiple return values"""
    return_tuple_is_single_item = enum.auto()

    f"""Flag to tell varvault that the return keys provided in a MiniVault being returned are split between multiple vaults decorating the same function. 
    By default, any return values from a decorated function must be able to be mapped to the keys defined as return keys. If two vaults are taking return values separately, 
    this wouldn't be possible. Usage of this flag REQUIRES that the return value is a MiniVault-object."""
    split_return_keys = enum.auto()

    f"""Flag to tell varvault to disable logger completely and not log anything to a log-file."""
    disable_logger = enum.auto()

    f"""Flag to ignore keys not in keyring when creating a vault from an existing vault-resource. If resource is configured as read-only, this behavior will be enabled by default."""
    ignore_keys_not_in_keyring = enum.auto()

    f"""Flag to tell varvault to delete an existing log file when creating a vault from an existing vault-file"""
    remove_existing_log_file = enum.auto()

    f"""Flag to tell varvault when using a vaulter-decorated function and not returning objects for all keys to not fail and just set the keys defined.
     If this is set, the return variables MUST be inside a MiniVault object, otherwise varvault cannot determine what variable belongs to what key."""
    return_key_can_be_missing = enum.auto()

    f"""Flag to tell a vaulter-decorated function to not log exceptions. Exceptions can sometimes be expected,
    and sometimes it might be preferable to not log errors using varvault and just log them normally."""
    no_error_logging = enum.auto()

    f"""Flag to tell varvault to use the keyword args in the signature of a decorated function to determine the keys to extract from the vault. This effectively removes 
    the need to define input keys through the decorator. Instead, you just need to define the input keys in the signature of the decorated function by calling the keyword 
    argument the same as the key. This will make tracking where the keys in the Keyring are used harder, but reduces the amount of boilerplate required. Can be defined 
    for the entire vault, or for a specific decorated function only."""
    use_signature_for_input_keys = enum.auto()
