"""
versions.py - Representations of the different API versions.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from enum import Enum

import logging
from functools import total_ordering

from Modules.context import Context

log = logging.getLogger(__name__)


@total_ordering
class Version(Enum):
    """
    Represents an API version with it's string representation and an integer representation for
    comparisons.

    These are comparable, where more recent API versions are 'greater' than older ones.

    Examples:
        >>> Version.V_20 < Version.V_21
        True
        >>> Version["V_20"] < Version("v2.1")
        True
        >>> Version.V_20 >= Version.V_21
        False
    """
    V_20 = "v2.0"
    V_21 = "v2.1"

    def __lt__(self, other):
        if isinstance(other, Version):
            return _version_int_values[self] < _version_int_values[other]
        else:
            return NotImplemented


_version_int_values = {
    Version.V_20: 200,
    Version.V_21: 210
}


def require_api_version(version: Version, exact: bool=False):
    """
    Decorate a command function to require a certain API version for its execution.
    If the check fails, a warning is logged. IRC stays quiet.

    Args:
        version: Needed API version.
        exact: If this is False, *version* is the minimum required version. Otherwise, the versions
               need to match exactly.
    """
    version = version.value
    def dec(fun):
        def wrapper(context: Context):
            actual_version: Version = context.bot.api_handler.api_version.value
            if exact and actual_version == version or actual_version >= version:
                return fun(context)
            else:
                log.warning(f"Command {context.words[0]} not executed as current API version "
                            f"{actual_version[0]} {'==' if exact else '>='} needed API version "
                            f"{version[0]}.")

        return wrapper
    return dec
