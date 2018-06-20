"""
search.py - Provides a facility to generate search queries to the API.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from typing import Callable, Dict, Tuple, Any, Union, Sequence

from utils.nested import set_nested
from utils.typechecking import check_type


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

            if sanitize is None:
                set_nested(result, json_key, value)
            else:
                set_nested(result, json_key, sanitize(value))

        return result
