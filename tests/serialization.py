def hash_dict(any_dict: dict) -> str:
    import hashlib

    return hashlib.md5(str(any_dict).encode()).hexdigest()


def serialize(value):
    if isinstance(value, str):
        return "'" + value + "'"
    elif isinstance(value, (bytes, int, list, tuple, dict, set, bool, type(None))):
        return str(value)
    else:
        print(
            f"Invalid type: {type(value)}, allowed types are: (bytes, int, tuple, list, dict, set, bool, NoneType)"
        )


def deserialize(value: str):
    import ast

    try:
        return ast.literal_eval(value)
    except ValueError:
        f"""Invalid value: {value} with type {type(value)}"""
    except SyntaxError:
        """Code injection detected."""
