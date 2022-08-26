import asyncio
import enum
from types import *
from typing import *

from .keyring import Keyring, Key
from .minivault import MiniVault
from .vaultstructs import VaultStructBase
from .resource import BaseResource


class AssignedByVaultEnum(enum.Enum):
    """
    Enum that represents the assigned_by_vault attribute of a variable.
    """
    ASSIGNED = True


AssignedByVault = AssignedByVaultEnum.ASSIGNED


def concurrent_execution(target: Union[Coroutine, FunctionType, Callable], *inputs, **kwargs):
    """
    Wraps the asyncio API in Python to make it a bit easier to work with.

    Example usage:
    ```
    async def run(arg1, arg2, const=None):
        assert const == "2"
        print(arg1, arg2)
        return (arg1 + arg2) * int(const)

    values = concurrent_execution(run, [1, 2, 3, 4, 5], [10, 20, 30, 40, 50], const="2")
    print(values)
    ```
    Output will be
    ```
    [22, 44, 66, 88, 110]
    ```

    :param target: A callable defined as coroutine via the keyword "async" that takes an arbitrary amount of arguments
    :param inputs: An arbitrary tuple of arguments as iterables. All iterables will be zipped together like this: zipped = list(zip(*inputs))
    :param kwargs: Kwargs that are treated like constants that will be sent to each call of 'target'. Any object in kwargs will NOT be zipped into the other arguments.
    :return: Whatever target returns, but as a list of what it returned.
    """
    assert asyncio.iscoroutinefunction(target), f"'target' ({target.__module__}.{target.__name__}) is not a coroutine function; define it as 'async def {target.__name__}(...)'"

    async def do(_target, *_inputs, **_kwargs):
        zipped = list(zip(*_inputs))
        _ret = await asyncio.gather(*[asyncio.create_task(_target(*i, **_kwargs)) for i in zipped])
        return _ret

    return asyncio.run(do(target, *inputs, **kwargs))


def create_mv_from_resource(varvault_filehandler_from: BaseResource, varvault_keyring: Type[Keyring], **extra_keys) -> MiniVault:
    f"""Creates a {MiniVault}-object from a file by loading the vault from the file using the {varvault_filehandler_from} passed."""
    assert isinstance(varvault_filehandler_from, BaseResource), f"'varvault_filehandler_from' must be an instance of {BaseResource}, not {type(varvault_filehandler_from)}"
    assert issubclass(varvault_keyring, Keyring), f"'varvault_keyring' must be a subclass of {Keyring}, not {varvault_keyring} ({type(varvault_keyring)})"
    vault_file_data = varvault_filehandler_from.read()

    assert isinstance(vault_file_data, dict), f"'vault_file_data' from the filehandler is not a dict: {vault_file_data}"

    # Get the keys from the keyring as a list.
    keys_from_keyring = varvault_keyring.get_keys()
    keys_from_keyring.update(extra_keys)
    return_vault_data = dict()

    async def build(key_in_file: str):
        if key_in_file not in keys_from_keyring:
            return
        key: Key = keys_from_keyring[key_in_file]
        if key.valid_type and issubclass(key.valid_type, VaultStructBase):
            return_vault_data[key] = key.valid_type.create(key_in_file, vault_file_data[key_in_file])
        else:
            if key.can_be_none and vault_file_data[key_in_file] is None:
                return_vault_data[key] = None
            else:
                assert key.valid_type is None or isinstance(vault_file_data[key_in_file], key.valid_type), f"Key type missmatch ({key}; Valid type {key.valid_type}, actual type: {type(vault_file_data[key_in_file])}"
                return_vault_data[key] = vault_file_data[key_in_file]

    concurrent_execution(build, vault_file_data.keys())

    return MiniVault(**return_vault_data)
