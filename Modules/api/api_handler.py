"""
api_handler.py - Abstract base class for API handlers. To be used comparably to a Java interface.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""

from typing import Union, List
from abc import ABC, abstractmethod, abstractproperty
from uuid import UUID

from Modules.api.versions import Version
from Modules.rat_board import RatBoard
from Modules.rat_rescue import Rescue
from Modules.rats import Rats


class APIHandler(ABC):
    """Defines the public interface of an API handler."""
    api_version: Version = abstractproperty()
    board: RatBoard = None
    """Board object updates from the API should be sent to. To be set by the board."""

    hostname = abstractproperty()
    token = abstractproperty()
    tls = abstractproperty()

    connected = abstractproperty()

    @abstractmethod
    def __init__(self, hostname: str, token: str=None, tls=True):
        """Initialize a new API handler object."""

    @abstractmethod
    async def connect(self):
        """
        Establish a connection to the API and check versions.

        Raises:
            NotConnectedError: If this instance is already connected. Shush.
            MismatchedVersionError: If the API runs a version this handler isn't for.
        """

    @abstractmethod
    async def disconnect(self):
        """
        Disconnect from the server.

        Raises:
            NotConnectedError: If this instance is not connected.
        """

    @abstractmethod
    async def modify(self, hostname: str=None, token: str=None, tls: bool=None):
        """Change hostname, token or tls properties."""

    @abstractmethod
    async def update_rescue(self, rescue: Rescue, full: bool=True):
        """
        Update a rescue's data in the API.

        Arguments:
            rescue (Rescue): Rescue to be updated in the API.
            full (bool): If this is True, all rescue data will be sent. Otherwise, only properties
                that have changed.

        Raises:
            ValueError: If *rescue* doesn't have its case ID set.
        """

    @abstractmethod
    async def create_rescue(self, rescue: Rescue) -> UUID:
        """
        Create a rescue within the API.

        Raises:
            ValueError: If the provided rescue already has its ID set.
        """

    @abstractmethod
    async def delete_rescue(self, rescue: Union[Rescue, UUID]):
        """
        Delete a rescue in the API.

        Arguments:
            rescue (Rescue or UUID): Rescue to delete. Can be either a UUID or a Rescue object.
                In the latter case, the rescue's ID must not be None.

        Raises:
            ValueError: If a Rescue object without its ID set was provided.
        """

    @abstractmethod
    async def get_rescues(self, **criteria) -> List[Rescue]:
        """Get all rescues from the API matching the criteria provided."""

    @abstractmethod
    async def get_rescue_by_id(self, id: Union[str, UUID]) -> Rescue:
        """Get rescue with the provided ID."""

    @abstractmethod
    async def get_rats(self, **criteria) -> List[Rats]:
        """Get all rats from the API matching the criteria provided."""

    @abstractmethod
    async def get_rat_by_id(self, id: Union[str, UUID]) -> Rats:
        """Get rat with the provided ID."""
