"""
search.py - Provides a facility to generate search queries to the API.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from abc import ABC, abstractmethod
from typing import Callable, Dict, Tuple, Any, Union, Sequence

from utils.nested import set_nested
from utils.typechecking import check_type


class _SequelizeOperator(ABC):
    @abstractmethod
    def generate(self, sanitize: Callable=None) -> Union[dict, list]:
        pass


class _UnaryOp(_SequelizeOperator):
    _op = None

    def __init__(self, value):
        self._value = value

    def generate(self, sanitize: Callable=None) -> dict:
        if sanitize is None:
            return {self._op: self._value}
        else:
            return {self._op: sanitize(self._value)}


class Not(_UnaryOp):
    _op = "$not"


class Contains(_UnaryOp):
    _op = "$contains"


class _SequenceOperator(_SequelizeOperator):
    _op = None

    def __init__(self, *values):
        self._values = values

    def generate(self, sanitize: Callable=None) -> dict:
        if sanitize is None:
            return {self._op: list(self._values)}
        else:
            return {self._op: [sanitize(value) for value in self._values]}


class In(_SequenceOperator):
    _op = "$in"


class NotIn(_SequelizeOperator):
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

            if types is not None:
                check_type(value, *types)

            if isinstance(value, _SequelizeOperator):
                set_nested(result, json_key, value.generate(sanitize))
            elif sanitize is None:
                set_nested(result, json_key, value)
            else:
                set_nested(result, json_key, sanitize(value))

        return result
