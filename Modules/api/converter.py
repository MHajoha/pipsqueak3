from abc import ABC
from enum import Enum, auto
from typing import Callable, Iterator

import asyncio


def get_nested(source: dict, key: str):
    current = source
    for subkey in key.split("."):
        current = current[subkey]

    return current

def set_nested(dest: dict, key: str, value):
    split_keys = key.split(".")
    current = dest
    for subkey in split_keys[:-1]:
        current = dest.setdefault(subkey, {})

    current[split_keys[-1]] = value


class Retention(Enum):
    MODEL_ONLY = auto()
    JSON_ONLY = auto()
    BOTH = auto()
    NONE = auto()


class _NotSet:
    pass


class Field(object):
    def __init__(self, json_path: str, attribute_name: str=None, constructor_arg: str=None,
                 to_obj: Callable=None, to_json: Callable=None, default=_NotSet, optional=False,
                 retention: Retention=Retention.BOTH):
        self.json_path = json_path
        self.attr_name = attribute_name
        self.constructor_arg = constructor_arg
        self.to_obj = to_obj
        self.to_json = to_json
        self.default = default
        self.optional = optional
        self.retention = retention

    def __set_name__(self, owner, name):
        if self.constructor_arg is None:
            self.constructor_arg = name
        if self.attr_name is None:
            self.attr_name = name

    async def from_json(self, json: dict):
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
        try:
            if self.to_json is None:
                return getattr(obj, self.attr_name)
            elif asyncio.iscoroutinefunction(self.to_json):
                return await self.to_obj(getattr(obj, self.attr_name))
            else:
                return self.to_obj(getattr(obj, self.attr_name))
        except AttributeError as e:
            if self.optional:
                return None
            else:
                raise KeyError(f"provided object does not have attribute {self.attr_name}") from e

    async def from_search_criteria(self, value):
        if self.to_json is None:
            return value
        elif asyncio.iscoroutinefunction(self.to_json):
            return await self.to_json(value)
        else:
            return self.to_json(value)


class Converter(ABC):
    _klass: type = None

    def __init_subclass__(cls, klass: type):
        cls._klass = klass

    @classmethod
    def _fields(cls) -> Iterator[Field]:
        return filter(lambda attr: isinstance(attr, Field), cls.__dict__.values())

    @classmethod
    def _field_for_arg(cls, arg: str) -> Field:
        return next(filter(lambda field: field.constructor_arg == arg, cls._fields()))

    @classmethod
    async def to_obj(cls, json: dict):
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
        json = {}
        for key, value in criteria.items():
            field = cls._field_for_arg(key)
            if field.retention in (Retention.JSON_ONLY, Retention.BOTH):
                set_nested(json, field.json_path.replace("attributes.", ""),
                           await field.from_search_criteria(value))

        return json
