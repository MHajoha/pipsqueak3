"""
versions.py - Representations of the different API versions.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from enum import Enum

class Version(Enum):
    V_20 = ["v2.0", 200]
    V_21 = ["v2.1", 210]
