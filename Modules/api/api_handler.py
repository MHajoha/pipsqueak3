"""
api_handler.py - Abstract base class for API handlers. To be used comparably to a Java interface.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from datetime import datetime
from typing import Union, List, Optional, Iterable
from abc import abstractmethod, abstractproperty, ABC
from uuid import UUID

from Modules.api.search import SequelizeOperator
from Modules.api.versions import Version
from Modules.mark_for_deletion import MarkForDeletion
from Modules.rat_board import RatBoard
from Modules.rat_quotation import Quotation
from Modules.rat_rescue import Rescue
from Modules.rat import Rat
from utils.ratlib import Status, Outcome, Platforms


_UNSET = object()


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
        """
        Initialize a new API Handler.

        Arguments:
            hostname (str): Hostname to connect to.
            token (str): OAuth token to be used for authorization or None if it's not needed.
            tls (bool): Whether to use TLS when connecting or not ('ws:' versus 'wss:').
        """

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
    async def update_rescue(self, rescue: Rescue, full: bool=True):
        """
        Update a rescue's data in the API.

        Arguments:
            rescue (Rescue): Rescue to be updated in the API.
            full (bool): If this is True, all rescue data will be sent. Otherwise, only properties
                that have changed.

        Raises:
            ValueError: If *rescue* doesn't have its case ID set.
            NotConnectedError: If this instance is not connected.
        """

    @abstractmethod
    async def create_rescue(self, rescue: Rescue) -> UUID:
        """
        Create a rescue within the API.

        Raises:
            ValueError: If the provided rescue already has its ID set.
            NotConnectedError: If this instance is not connected.
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
            NotConnectedError: If this instance is not connected.
        """

    @abstractmethod
    async def get_rescues(self, *,
                          id: Union[UUID, SequelizeOperator[UUID]]=_UNSET,
                          client: Union[str, SequelizeOperator[str]]=_UNSET,
                          system: Union[str, SequelizeOperator[str]]=_UNSET,
                          status: Union[Status, SequelizeOperator[Status]]=_UNSET,
                          unidentified_rats: Union[Iterable[str],
                                                   SequelizeOperator[Iterable[str]]]=_UNSET,
                          created_at: Union[datetime, SequelizeOperator[datetime]]=_UNSET,
                          updated_at: Union[datetime, SequelizeOperator[datetime]]=_UNSET,
                          quotes: Union[Iterable[Quotation],
                                        SequelizeOperator[Iterable[Quotation]]]=_UNSET,
                          title: Union[str, SequelizeOperator[Optional[str]], None]=_UNSET,
                          code_red: Union[bool, SequelizeOperator[bool]]=_UNSET,
                          first_limpet: Union[Rat, SequelizeOperator[Rat]]=_UNSET,
                          marked_for_deletion: Union[MarkForDeletion,
                                                     SequelizeOperator[MarkForDeletion]]=_UNSET,
                          irc_nickname: Union[str, SequelizeOperator[str]]=_UNSET,
                          lang_id: Union[str, SequelizeOperator[str]]=_UNSET,
                          outcome: Union[Outcome,
                                         SequelizeOperator[Optional[Outcome]], None]=_UNSET,
                          platform: Union[Platforms, SequelizeOperator[Platforms]]=_UNSET
                          ) -> List[Rescue]:
        """
        Get all rescues from the API matching the criteria provided.
        A criterion can be wrapped in a subclass of :class:`SequelizeOperator`.

        All API handlers must implement the following parameters, but may add more.
        Such extra parameters should only be used after checking the handler's version.

        Arguments:
            id (UUID)
            client (str)
            system (str)
            status (Status)
            unidentified_rats (list of str)
            created_at (datetime)
            updated_at (datetime)
            quotes (list of Quotation)
            title (str)
            code_red (bool)
            first_limpet (Rat)
            marked_for_deletion (MarkForDeletion)
            irc_nickname (str)
            lang_id (str)
            outcome (Outcome)
            platform (Platforms)

        Raises:
            NotConnectedError: If this instance is not connected.
        """

    @abstractmethod
    async def get_rescue_by_id(self, id: Union[str, UUID]) -> Rescue:
        """
        Get rescue with the provided ID.

        Raises:
            NotConnectedError: If this instance is not connected.
        """

    @abstractmethod
    async def get_rats(self, *,
                       id: Union[UUID, SequelizeOperator[UUID]]=_UNSET,
                       name: Union[str, SequelizeOperator[str]]=_UNSET,
                       platform: Union[Platforms, SequelizeOperator[Platforms]]=_UNSET
                       ) -> List[Rat]:
        """
        Get all rats from the API matching the criteria provided.

        Raises:
            NotConnectedError: If this instance is not connected.
        """

    @abstractmethod
    async def get_rat_by_id(self, id: Union[str, UUID]) -> Rat:
        """
        Get rat with the provided ID.

        Raises:
            NotConnectedError: If this instance is not connected.
        """
