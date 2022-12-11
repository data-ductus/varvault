import re
import inspect
import warnings
import functools

from typing import Callable

from .utils import assert_and_raise

_VALIDATOR = "_validator"
_MODIFIER = "_modifier"


class ValidatorException(Exception):
    pass


class ModifierException(Exception):
    pass


def validator(function_asserts: bool = None, function_returns_bool: bool = None, skip_source_assertions: bool = False) -> Callable:
    f"""
    Decorator that is used to register a function as a validator-function used for varvault-keys.
    A validator-function assigned to a key will be executed based on how it's registered.
    
    If no argument is passed to the decorator, {function_asserts} will be set to {True}.

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

        setattr(func, _VALIDATOR, True)

        @functools.wraps(func)
        def wrap_inner(keyvalue: object, key):
            if function_asserts:
                try:
                    func(keyvalue)
                except AssertionError as e:
                    raise ValidatorException(f"{e} for key '{key}'") from e
            elif function_returns_bool:
                ret = func(keyvalue)
                assert_and_raise(isinstance(ret, bool), ValidatorException(f"The return value is of type {type(ret)}, not of type {bool}, and you have said "
                                                                           f"that the function will return a bool through 'function_returns_bool' being set to {True}"))
                assert_and_raise(ret, ValidatorException(f"Validator-function {func.__name__} returned {False} for key '{key}' with value: {keyvalue}"))
        return wrap_inner
    return wrap_outer


def modifier() -> Callable:
    f"""
    Decorator that is used to register a function as a modifier-function used for varvault-keys.
    A modifier-function will change the value of object assigned to the key before it's written to the vault. A good example of this is 
    to, for example, change the path of a file to an absolute path, or expand user/vars in the path of the file. 
    It can also be used to strip a sequence of characters from a string, or to change the case of a string.
    """

    def wrap_outer(func: Callable) -> Callable:

        assert callable(func), f"Object {func} is not a callable"
        argspecs = inspect.getfullargspec(func)

        assert len(argspecs.args) == 1, f"You've defined more arguments (or no arguments) for the validator function than you are allowed to. There must be exactly one argument defined in the signature."
        source = inspect.getsource(func)
        assert re.findall(re.compile(r".*return .*"), source), "No return-statement found in the functions source. That doesn't seem right if you are planning to modify the value of the object."
        from varvault import Key
        setattr(func, _MODIFIER, True)

        @functools.wraps(func)
        def wrap_inner(keyvalue: object, key: Key):
            try:
                return func(keyvalue)
            except Exception as e:
                raise ModifierException(f"{e} for key '{key}'") from e
        return wrap_inner
    return wrap_outer
