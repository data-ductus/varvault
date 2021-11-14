import asyncio
import logging
from types import *
from typing import *

from .keyring import Keyring, Key
from .minivault import MiniVault
from .vaultstructs import VaultStructBase


def md5hash(fname):
    """Get md5 hash of a file using hashlib"""
    import hashlib

    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def is_serializable(obj: object, logger: logging.Logger = None):
    import json

    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError) as e:
        if logger:
            logger.debug(f"Failed to serialize object: {e}")
        return False


def concurrently(*args_as_iterable: Union[Sized, Iterable], **input_kwargs):
    """
    Decorator for running a coroutine-function concurrently.

    Example:

    ```
    @concurrently([1, 2, 3, 4, 5], (10, 20, 30, 40), const="2")
    async def run(k, v, const=None):
        print(k, v, const)
        return k * v


    if __name__ == '__main__':
        print(run())
    ```

    Output:

    ```
    1 10 const
    2 20 const
    3 30 const
    4 40 const
    [10, 40, 90, 160]  # This is from printing the result from run()
    ```

    Note that the 5th item in the first list was ignored because the second iterable only included 4 elements. This is due to 'zip'.
    Filling out the tuple with None as the 5th element would make it work.

    :param args_as_iterable: The arguments as iterables to pass to the decorated function. The arguments are combined using the builtin keyword 'zip'.
    :param input_kwargs: Args passed as constants to the function, i.e. these variables will be sent to every call for the decorated function.
    """
    import functools
    import asyncio

    def wrap_outer(func: Union[Coroutine, FunctionType, Callable]):
        assert asyncio.iscoroutinefunction(func), f"Function {func.__module__}.{func.__name__} is not defined as a coroutine; define it as 'async def {func.__name__}(...)'"

        @functools.wraps(func)
        def wrap_inner(*args, **kwargs):
            # Don't use args or kwargs; That's not how this is meant to be used
            assert len(args) == 0 and len(kwargs) == 0, f"You should not pass arguments to this function ({func.__module__}.{func.__name__}) when it's decorated with '{concurrently.__module__}.{concurrently.__name__}'. Arguments should come from the decorator."
            return concurrent_execution(func, *args_as_iterable, **input_kwargs)

        return wrap_inner
    return wrap_outer


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


def create_return_vault_from_file(filename_from: str, keyring: Type[Keyring], live_update=False, **extra_keys) -> MiniVault:
    import json

    assert issubclass(keyring, Keyring)
    vault_file_data = dict()
    try:
        vault_file_data = json.load(open(filename_from))
    except FileNotFoundError as e:
        if not live_update:
            raise
        pass
    assert isinstance(vault_file_data, dict)

    # Get the keys from the file as a list.
    keys_from_keyring = keyring.get_keys_in_keyring()
    keys_from_keyring.update(extra_keys)
    return_vault_data = dict()

    async def build(key_in_file: str):
        if key_in_file not in keys_from_keyring:
            return
        key: Key = keys_from_keyring[key_in_file]
        if issubclass(key.valid_type, VaultStructBase):
            return_vault_data[key] = key.valid_type.build_from_vault_key(key_in_file, vault_file_data[key_in_file])
        else:
            if key.can_be_none and vault_file_data[key_in_file] is None:
                return_vault_data[key] = None
            else:
                assert isinstance(vault_file_data[key_in_file], key.valid_type), f"Key type missmatch ({key}; Valid type {key.valid_type}, actual type: {type(vault_file_data[key_in_file])}"
                return_vault_data[key] = vault_file_data[key_in_file]

    concurrent_execution(build, vault_file_data.keys())

    return MiniVault(**return_vault_data)
