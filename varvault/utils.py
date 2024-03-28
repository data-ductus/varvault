import enum


class AssignedByVaultEnum(enum.Enum):
    """
    Enum that represents the assigned_by_vault attribute of a variable.
    """
    ASSIGNED = True


AssignedByVault = AssignedByVaultEnum.ASSIGNED


def assert_and_raise(condition: bool, exception: BaseException):
    """
    Asserts a condition and raises an exception if the condition is False.
    Note: Checks if __debug__ is set to True before running the assertion, just how builtin `assert` works.

    :param condition: The condition to assert
    :param exception: The exception to raise
    """
    if __debug__ and not condition:
        raise exception
