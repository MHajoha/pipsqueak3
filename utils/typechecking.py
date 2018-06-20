"""
typechecking.py - Provides utility functions for type checking objects.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""

def check_type(value, type1: type, *more_types: type):
    """
    Utility function to check the type of an object.
    Raises a :class:`TypeError` if the object has None of the required types.

    Args:
        value:
            The object to be type-checked.
        type1:
            The first type which *value* may have. This extra argument ensures that at least one
            type is provided.
        *more_types:
            Any number of other types.

    Raises:
        TypeError: If the object is an instance of none of the provided types.
                   Message format is 'expected: type1, ... . actual: type of *value*'

    Examples:
        >>> check_type("hello there", str)

        >>> check_type(5, str, dict, list)
        Traceback (most recent call last):
            ...
        TypeError: expected: str, dict, list. actual: int
    """
    types = (type1, *more_types)
    if not any(map(lambda type_: isinstance(value, type_), types)):
        raise TypeError(f"expected: {', '.join(type_.__name__ for type_ in types)}. "
                        f"actual: {type(value).__name__}")
