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

from ratlib.nested import get_nested, set_nested


class AnyOf(object):
    """To mark in a search that a criterion can be one of several options."""
    def __init__(self, *args):
        self.options = args

    def __iter__(self):
        return iter(self.options)


class Not(object):
    """To mark in a search that a criterion can be anything but a certain value."""
    def __init__(self, value):
        self.value = value


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


UNSET = object()


class Field(object):
    """
    An object to describe how a converter should convert the attributes of an object between it's
    JSON form coming from the API and our things. Only valid in a Converter class.
    """
    def __init__(self, json_path: str, attribute_name: str=None, constructor_arg: str=None,
                 to_obj: Callable=None, to_json: Callable=None, default=UNSET,
                 retention: Retention=Retention.BOTH, criterion: str=None):
        """
        Create a new converter field.

        Args:
            json_path: Location of the attribute within the API JSON object. See `get_nested`.
            attribute_name: Name of the corresponding attribute on our object. Defaults to the name
                of the field this instance is assigned to within the converter class.
            constructor_arg: Name of the argument to the constructor of our object. Defaults as
                *attribute_name* does.
            to_obj: An optional sanitation function receiving the original value and returning a
                new one, which will be used instead. If this returns `UNSET`, then the constructor
                argument will be omitted entirely. Can also be a coroutine.
            to_json: Analogous to *_to_obj* for converting to the JSON representation.
            default: A _default value or field for the json-to-model conversion to use if
                *json_path* is not present in the json.
            retention: Where the field applies. See :class:`Retention`.
        """
        self._json_path = json_path
        self._attr_name = attribute_name
        self._constructor_arg = constructor_arg
        self._to_obj = to_obj
        self._to_json = to_json
        self._default = default
        self._retention = retention
        self._criterion = criterion

    json_path = property(lambda self: self._json_path)
    attr_name = property(lambda self: self._attr_name)
    constructor_arg = property(lambda self: self._constructor_arg)
    retention = property(lambda self: self._retention)
    criterion = property(lambda self: self._criterion)

    def __set_name__(self, owner, name):
        """
        Facilitates `_attr_name` and `_constructor_arg` defaulting to the name of the field this
        instance is assigned to.
        """
        if self._constructor_arg is None:
            self._constructor_arg = name
        if self._attr_name is None:
            self._attr_name = name

    async def from_json(self, json: dict):
        """
        Retrieve this field's resulting value from a JSON dict.
        """
        try:
            if self._to_obj is None:
                return get_nested(json, self._json_path)
            elif asyncio.iscoroutinefunction(self._to_obj):
                return await self._to_obj(get_nested(json, self._json_path))
            else:
                return self._to_obj(get_nested(json, self._json_path))
        except KeyError as e:
            if isinstance(self._default, Field):
                return await self._default.from_json(json)
            elif self._default is not UNSET:
                return self._default
            else:
                raise KeyError(f"{self._json_path} not found in provided json dict") from e

    async def from_model(self, obj):
        """
        Retrieve this field's resulting value from one of our objects.
        """
        try:
            return await self.from_obj_value(getattr(obj, self._attr_name))
        except AttributeError as e:
            raise KeyError(f"provided object does not have attribute {self._attr_name}") from e

    async def from_obj_value(self, value):
        """
        Return *value* sanitized to be used in the JSON representation.
        """
        if self._to_json is None:
            return value
        elif asyncio.iscoroutinefunction(self._to_json):
            return await self._to_json(value)
        else:
            return self._to_json(value)


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
    def _field_for_criterion(cls, criterion: str) -> Field:
        """
        Find the field on this converter for the given criterion.

        Raises:
            KeyError: If this converter has no fitting field.
        """
        try:
            return next(filter(lambda field: field.criterion == criterion, cls._fields()))
        except StopIteration as e:
            raise KeyError(criterion) from e

    @classmethod
    async def to_obj(cls, json: dict):
        """Convert the provided JSON to an object of whatever class this converter is for."""
        constructor_args = {}
        for field in cls._fields():
            if field.retention in (Retention.MODEL_ONLY, Retention.BOTH):
                result = await field.from_json(json)
                if result is UNSET:
                    continue
                else:
                    constructor_args[field.constructor_arg] = result

        return await cls.final_to_obj(cls._klass(**constructor_args))

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
                if result is UNSET:
                    continue
                else:
                    set_nested(json, field.json_path, result)

        return await cls.final_to_json(json)

    @classmethod
    async def to_search_parameters(cls, criteria: dict) -> dict:
        """
        Sanitize the provided dict of criterion with the appropriate field of this converter.
        """
        json = {}
        for key, value in criteria.items():
            field = cls._field_for_criterion(key)
            if isinstance(value, AnyOf):
                result = [await field.from_obj_value(item) for item in value]
            elif isinstance(value, Not):
                result = {"$not": await field.from_obj_value(value.value)}
            else:
                result = await field.from_obj_value(value)

            set_nested(json, field.json_path.replace("attributes.", ""), result)

        return json

    @classmethod
    async def final_to_obj(cls, obj: _klass) -> _klass:
        """
        A function to optionally be overridden by converters to do a last bit of sanitation when the
        object itself has been constructed.
        """
        return obj

    @classmethod
    async def final_to_json(cls, json: dict) -> dict:
        """
        A function to optionally be overridden by converters to do a last bit of sanitation when the
        JSON dict has been constructed.
        """
        return json
