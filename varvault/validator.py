import re
import inspect
import warnings
import functools

from typing import Callable


def validator(function_asserts: bool = None, function_returns_bool: bool = None, skip_source_assertions: bool = False) -> Callable:
    f"""
    Decorator that is used to register a function as a validator-function used for varvault-keys.
    A validator-function assigned to a key will be executed based on how it's registered.
    
    If no argument is passed to the function, {function_asserts} will be set to {True}.

    :param function_asserts: Used to tell varvault that the validator-function will do the validation by performing an assert
    :param function_returns_bool: Used to tell varvault that the validator-function will return a boolean that varvault will assert to be True.
    :param skip_source_assertions: Used to tell this decorator to skip source-assertions that verify that assert or return is done in the validator-function.  
    """
    assert isinstance(function_asserts, bool) or function_asserts is None, f"'function_asserts' must be a bool, or {None}"
    assert isinstance(function_returns_bool, bool) or function_returns_bool is None, f"'function_returns_bool' must be a bool, or {None}"
    if function_asserts and function_returns_bool:
        raise SyntaxError("You've set both 'function_asserts' and 'function_returns_bool' to True; 'function_asserts' takes precedence. Is this what you really want?")
    if not function_asserts and not function_returns_bool:
        function_asserts = True

    def wrap_outer(func: Callable) -> Callable:

        assert callable(func), f"Object {func} is not a callable"
        argspecs = inspect.getfullargspec(func)

        assert len(argspecs.args) == 1, f"You've defined more arguments (or no arguments) for the validator function than you are allowed to. There must be exactly one argument defined in the signature."

        source = inspect.getsource(func)
        if function_asserts:
            assert re.findall(re.compile(r".*assert .*"), source) or skip_source_assertions, "No assert-statement found in the functions source. That doesn't seem right if you are planning to do an assert in the function. Set 'skip_source_assertions=True' to skip it"
        elif function_returns_bool:
            if argspecs.annotations.get("return") != bool:
                warnings.warn("If you define the validator-function to say that it returns a bool, you should really also annotate the function to say it returns a bool.", SyntaxWarning)
            assert re.findall(re.compile(r".*return .*"), source) or skip_source_assertions, "No return-statement found in the functions source. That doesn't seem right if you are planning to return a bool that varvault is meant to assert. Set 'skip_source_assertions=True' to skip"

        @functools.wraps(func)
        def wrap_inner(keyvalue: object):
            assert callable(func), f"Function {func} is not a callable"
            if function_asserts:
                func(keyvalue)
            elif function_returns_bool:
                ret = func(keyvalue)
                assert isinstance(ret, bool), f"The return value is of type {type(ret)}, not of type {bool}, " \
                                              f"and you have said that the function will return a bool through 'function_returns_bool' being set to {True}"
                assert ret is True, f"The validator-function {func.__name__} returned False for key-value: {keyvalue}"
        return wrap_inner
    return wrap_outer
