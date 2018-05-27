"""
converter.py - A helper module used by the api handler.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from abc import ABC
from enum import Enum, auto
from typing import Callable, Iterator

import asyncio


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
        current = dest.setdefault(subkey, {})

    current[split_keys[-1]] = value


class Retention(Enum):
    """
    Enum to control where certain attributes are included.

    Choices:
        * MODEL_ONLY: The field is ignored when converting to JSON.
        * JSON_ONLY: The field is ignored when converting to our object.
        * BOTH: The field is never ignored.
        * NONE: The field is always ignored.
    """
    MODEL_ONLY = auto()
    JSON_ONLY = auto()
    BOTH = auto()
    NONE = auto()


class _NotSet:
    """To allow me to use None as an argument while still dynamically selecting a default value."""
    pass


class Field(object):
    """
    An object to describe how a converter should convert the attributes of an object between it's
    JSON form coming from the API and our things. Only valid in a Converter class.
    """
    def __init__(self, json_path: str, attribute_name: str=None, constructor_arg: str=None,
                 to_obj: Callable=None, to_json: Callable=None, default=_NotSet,
                 retention: Retention=Retention.BOTH):
        """
        Create a new converter field.

        Args:
            json_path: Location of the attribute within the API JSON object. See `get_nested`.
            attribute_name: Name of the corresponding attribute on our object. Defaults to the name
                of the field this instance is assigned to within the converter class.
            constructor_arg: Name of the argument to the constructor of our object. Defaults as
                *attribute_name* does.
            to_obj: An optional sanitation function receiving the original value and returning a
                new one, which will be used instead. If this returns None, then the constructor
                argument will be omitted entirely. Can also be a coroutine.
            to_json: Analogous to *to_obj*.
            default: A default value or field for the json-to-model conversion to use if
                *json_path* is not present in the json.
            retention: Where the field applies. See :class:`Retention`.
        """
        self.json_path = json_path
        self.attr_name = attribute_name
        self.constructor_arg = constructor_arg
        self.to_obj = to_obj
        self.to_json = to_json
        self.default = default
        self.retention = retention

    def __set_name__(self, owner, name):
        """
        Facilitates `attr_name` and `constructor_arg` defaulting to the name of the field this
        instance is assigned to.
        """
        if self.constructor_arg is None:
            self.constructor_arg = name
        if self.attr_name is None:
            self.attr_name = name

    async def from_json(self, json: dict):
        """
        Retrieve this field's resulting value from a JSON dict.
        """
        try:
            if self.to_obj is None:
                return get_nested(json, self.json_path)
            elif asyncio.iscoroutinefunction(self.to_obj):
                return await self.to_obj(get_nested(json, self.json_path))
            else:
                return self.to_obj(get_nested(json, self.json_path))
        except KeyError as e:
            if isinstance(self.default, Field):
                return await self.default.from_json(json)
            elif self.default is not _NotSet:
                return self.default
            else:
                raise KeyError(f"{self.json_path} not found in provided json dict") from e

    async def from_model(self, obj):
        """
        Retrieve this field's resulting value from one of our objects.
        """
        try:
            if self.to_json is None:
                return getattr(obj, self.attr_name)
            elif asyncio.iscoroutinefunction(self.to_json):
                return await self.to_obj(getattr(obj, self.attr_name))
            else:
                return self.to_obj(getattr(obj, self.attr_name))
        except AttributeError as e:
            raise KeyError(f"provided object does not have attribute {self.attr_name}") from e

    async def from_search_criteria(self, value):
        """
        Return *value* sanitized to be used as criteria in a request to the API.
        """
        if self.to_json is None:
            return value
        elif asyncio.iscoroutinefunction(self.to_json):
            return await self.to_json(value)
        else:
            return self.to_json(value)


class Converter(ABC):
    """
    Base class for converters. Converters aren't instantiated and the class they target must be
    provided as an argument during the creation of the converter class.

    Example:
        >>> class MyFunkyConverter(Converter, klass=int):
        ...     pass # field declarations...
    """
    _klass: type = None
    """Holds the class this converter is for."""

    def __init_subclass__(cls, klass: type):
        """Facilitates setting klass with an argument during converter class creation."""
        cls._klass = klass

    @classmethod
    def _fields(cls) -> Iterator[Field]:
        """This converter's fields."""
        return filter(lambda attr: isinstance(attr, Field), cls.__dict__.values())

    @classmethod
    def _field_for_arg(cls, arg: str) -> Field:
        """
        The field on this converter with the specified constructor argument.

        Raises:
            ValueError: If this converter has no such field.
        """
        try:
            return next(filter(lambda field: field.constructor_arg == arg, cls._fields()))
        except StopIteration as e:
            raise ValueError(arg) from e

    @classmethod
    async def to_obj(cls, json: dict):
        """Convert the provided JSON to an object of whatever class this converter is for."""
        constructor_args = {}
        for field in cls._fields():
            if field.retention in (Retention.MODEL_ONLY, Retention.BOTH):
                result = await field.from_json(json)
                if result is None:
                    continue
                else:
                    constructor_args[field.constructor_arg] = result

        return cls._klass(**constructor_args)

    @classmethod
    async def to_json(cls, obj) -> dict:
        """
        Convert the provided object (which must be an instance of this converter's `klass`) to
        JSON ready for shipping.
        """
        json = {}
        for field in cls._fields():
            if field.retention in (Retention.JSON_ONLY, Retention.BOTH):
                result = await field.from_model(obj)
                if result is None:
                    continue
                else:
                    set_nested(json, field.json_path, result)

        return json

    @classmethod
    async def to_search_parameters(cls, criteria: dict) -> dict:
        """
        Sanitize the provided dict of criteria, treating them as arguments to our object's
        constructor.
        """
        json = {}
        for key, value in criteria.items():
            field = cls._field_for_arg(key)
            if field.retention in (Retention.JSON_ONLY, Retention.BOTH):
                set_nested(json, field.json_path.replace("attributes.", ""),
                           await field.from_search_criteria(value))

        return json
