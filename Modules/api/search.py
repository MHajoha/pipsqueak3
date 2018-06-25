"""
search.py - Provides a facility to generate search queries to the API.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from abc import abstractmethod
from typing import Callable, Dict, Tuple, Any, Union, Sequence, Generic, TypeVar

from utils.abstract import abstract
from utils.nested import set_nested
from utils.typechecking import check_type


T = TypeVar("T")
@abstract
class SequelizeOperator(Generic[T]):
    @abstractmethod
    def generate(self, sanitize: Callable=None) -> Union[dict, list]:
        pass


class _UnaryOp(SequelizeOperator[T], Generic[T]):
    _op: str = None

    def __init__(self, value: T):
        self._value: T = value

    def generate(self, sanitize: Callable=None) -> dict:
        if sanitize is None or self._value is None:
            return {self._op: self._value}
        else:
            return {self._op: sanitize(self._value)}


class Not(_UnaryOp[T], Generic[T]):
    _op = "$not"


class Contains(_UnaryOp[T], Generic[T]):
    _op = "$contains"


class _SequenceOperator(SequelizeOperator[T], Generic[T]):
    _op = None

    def __init__(self, *values: T):
        self._values: Tuple[T] = values

    def generate(self, sanitize: Callable=None) -> dict:
        if sanitize is None:
            return {self._op: list(self._values)}
        else:
            return {self._op: [None if value is None else sanitize(value)
                               for value in self._values]}


class In(_SequenceOperator[T], Generic[T]):
    _op = "$in"


class NotIn(_SequenceOperator[T], Generic[T]):
    _op = "$notIn"


class Search(object):
    def __init__(self):
        self._criteria: Dict[str, Tuple[str, Tuple[type], Callable]] = {}

    def add(self, criterion: str, json_key: str,
            types: Union[type, Sequence[type]]=None,
            sanitize: Callable=None, nullable: bool=False):
        if isinstance(types, type):
            types = types,
        if nullable:
            types = *types, type(None)

        self._criteria[criterion] = (json_key,
                                     (types,) if isinstance(types, type) else types,
                                     sanitize)

    def generate(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in criteria.items():
            json_key, types, sanitize = self._criteria[key]

            if isinstance(value, SequelizeOperator):
                set_nested(result, json_key, value.generate(sanitize))
            elif types is not None:
                check_type(value, *types)

                if sanitize is None or value is None:
                    set_nested(result, json_key, value)
                else:
                    set_nested(result, json_key, sanitize(value))

        return result
