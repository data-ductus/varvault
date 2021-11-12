from __future__ import annotations


class VaultFlags(str):
    """Class that represents flags that may be used for a vaulted
    function to tweak the behavior of the vaulted function."""

    _RETURN_VALUES_CANNOT_BE_NONE = "return_values_cannot_be_none"
    _PERMIT_MODIFICATIONS = "permit_modifications"
    _INPUT_VAR_CAN_BE_MISSING = "input_var_can_be_missing"
    _CLEAN_RETURN_VAR_KEYS = "clean_return_var_keys"
    _DEBUG = "debug"
    _SILENT = "silent"
    _LIVE_UPDATE = "live_update"
    _RETURN_TUPLE_IS_SINGLE_ITEM = "return_tuple_is_single_item"
    _SPLIT_RETURN_KEYS = "split_return_keys"

    def __new__(cls, name, *args, **kwargs):
        obj = super().__new__(cls, name)
        obj.name = name
        return obj

    def __eq__(self, other):
        if not isinstance(other, (str, VaultFlags)):
            return False
        elif isinstance(other, VaultFlags):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other

    @staticmethod
    def flag_is_set(flag: VaultFlags, *flags: VaultFlags):
        """This is not a flag. This function checks if a flag exists among a bunch of flags"""
        return flag in flags

    @staticmethod
    def return_values_cannot_be_none():
        f"""Flag to set if return values must be something other than {None}. By default, this is fine, but you can enforce return variables to be something other than {None}"""
        return VaultFlags(VaultFlags._RETURN_VALUES_CANNOT_BE_NONE)

    @staticmethod
    def permit_modifications():
        f"""Flag to set if variables may be modified either in the vault itself or for a specific decorated function. 
        By default, varvault doesn't permit modifications to existing keys as this can cause unintended behavior."""
        return VaultFlags(VaultFlags._PERMIT_MODIFICATIONS)

    @staticmethod
    def input_var_can_be_missing():
        f"""Flag to set if an input variable may be missing in a vault when it is accessed. In this case, the key will be sent to kwargs but it will be mapped to {None}."""
        return VaultFlags(VaultFlags._INPUT_VAR_CAN_BE_MISSING)

    @staticmethod
    def clean_return_var_keys():
        f"""Flag to clean return keys in a vault defined for a decorated function. This can be used during a cleanup stage. 
        Varvault will try to map the key to a default value for the valid type, like for example str(), or list(). If it doesn't work, the key will be mapped to {None}."""
        return VaultFlags(VaultFlags._CLEAN_RETURN_VAR_KEYS)

    @staticmethod
    def debug():
        f"""Flag to enable debug mode for logger output to the console to help you with debugging. By default, varvault will write debug logs to the logfile, but not the console. 
        By setting this, you'll have a much easier time debugging unintended behavior. Using this and {VaultFlags.silent} in conjunction will cancel each other out and make logging the default."""
        return VaultFlags(VaultFlags._DEBUG)

    @staticmethod
    def silent():
        f"""Flag to enable silent mode for a vault. This will completely remove debug logs being written to the logfile. This can be used to reduce unnecessary
         bloat and make debugging much more easy to do. Using this and {VaultFlags.debug} in conjunction will cancel each other out and make logging the default."""
        return VaultFlags(VaultFlags._SILENT)

    @staticmethod
    def live_update():
        f"""Flag to enable live-update of a vault file. If this is set, the vault will try to update its contents from an existing vault file if the contents of the file
         has changed since last time (this is determined by getting an md5 hash of the contents of the file). The live-update is only performed when the vault is accessed via the decorator."""
        return VaultFlags(VaultFlags._LIVE_UPDATE)

    @staticmethod
    def return_tuple_is_single_item():
        f"""Flag to tell varvault that the return value is a tuple that should be mapped to a single return-key. Varvault cannot tell if 
        a tuple is multiple return values or a single item meant for a single key as this how Python handles multiple return values"""
        return VaultFlags(VaultFlags._RETURN_TUPLE_IS_SINGLE_ITEM)

    @staticmethod
    def split_return_keys():
        f"""Flag to tell varvault that the return keys provided in a MiniVault being returned are split between multiple vaults decorating the same function. 
        By default, any return values from a decorated function must be able to be mapped to the keys defined as return keys. If two vaults are taking return values separately, 
        this wouldn't be possible. Usage of this flag REQUIRES that the return value is a MiniVault-object."""
        return VaultFlags(VaultFlags._SPLIT_RETURN_KEYS)
