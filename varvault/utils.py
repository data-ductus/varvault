import asyncio
import enum
from types import *
from typing import *


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


def assert_and_raise(condition: bool, exception: BaseException):
    """
    Asserts a condition and raises an exception if the condition is False.
    Note: Checks if __debug__ is set to True before running the assertion, just how builtin `assert` works.

    :param condition: The condition to assert
    :param exception: The exception to raise
    """
    if __debug__ and not condition:
        raise exception
