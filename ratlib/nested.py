"""
nested.py - Utility functions for messing with nested dicts.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""


def get_nested(source: dict, key: str):
    """
    Get a value from a nested dict.

    Arguments:
        source (dict): The top-level dict to begin in.
        key (str): A single key for the provided dict or a series of keys for nested dicts inside
            it, delimited by '.' characters.

    Raises:
        KeyError: If at any point the next key is not present in the current dict.
        TypeError: If *key* references something within a non-subscriptable object (i.e. not a
            dict).

    Example:
        >>> get_nested({"first": {"second": 42}}, "first.second")
        42
    """
    current = source
    for subkey in key.split("."):
        current = current[subkey]

    return current


def set_nested(dest: dict, key: str, value):
    """
    Set a value in a nested dict, creating any missing dicts along the way.
    Analogous to `get_nested`.

    Arguments:
        dest (dict): The top-level dict to begin traversal in.
        key (str): A single key for the provided dict or a series of keys for nested dicts inside
            it, delimited by '.' characters.
        value: The value to be set.

    Raises:
        KeyError: If at any point the next key is not present in the current dict.
        TypeError: If *key* references something within a non-subscriptable object (i.e. not a
            dict).

    Example:
        >>> set_nested({}, "first.second", 42)
    """
    split_keys = key.split(".")
    current = dest
    for subkey in split_keys[:-1]:
        current = current.setdefault(subkey, {})

    current[split_keys[-1]] = value
