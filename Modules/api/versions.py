"""
versions.py - Representations of the different API versions.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from enum import Enum

import logging

from Modules.context import Context

log = logging.getLogger(__name__)


class Version(Enum):
    """
    Represents an API version with it's string representation and a string representation for
    comparisons.
    """
    V_20 = ["v2.0", 200]
    V_21 = ["v2.1", 210]


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
            if exact and actual_version[1] == version[1] or actual_version[1] >= version[1]:
                return fun(context)
            else:
                log.warning(f"Command {context.words[0]} not executed as current API version "
                            f"{actual_version[0]} {'==' if exact else '>='} needed API version "
                            f"{version[0]}.")

        return wrapper
    return dec
