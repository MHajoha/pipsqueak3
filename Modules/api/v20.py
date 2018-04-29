"""
exceptions.py - Handler(s) for API v2.0

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from datetime import datetime
from typing import Dict, Any, Union, Set

from uuid import UUID

import functools

from Modules.api.converter import Converter, Field, Retention
from Modules.rat_quotation import Quotation
from Modules.rat_rescue import Rescue
from Modules.rats import Rats
from .api_handler import APIHandler
from .websocket import WebsocketRequestHandler


class QuotationConverter(Converter, klass=Quotation):
    datetime_to_str = functools.partial(datetime.strftime, fmt="%Y-%m-%dT%H:%M:%S.%f")
    str_to_datetime = functools.partial(datetime.strptime, format="%Y-%m-%dT%H:%M:%S.%f")

    message = Field("message")
    author = Field("author")
    created_at = Field("createdAt", to_obj=str_to_datetime, to_json=datetime_to_str),
    updated_at = Field("updatedAt", to_obj=str_to_datetime, to_json=datetime_to_str),
    last_author = Field("lastAuthor")

class RescueConverter(Converter, klass=Rescue):
    datetime_to_str = functools.partial(datetime.strftime, fmt="%Y-%m-%dT%H:%M:%S.%fZ")
    str_to_datetime = functools.partial(datetime.strptime, format="%Y-%m-%dT%H:%M:%S.%fZ")

    case_id = Field("id", to_obj=UUID, to_json=str)
    client = Field("attributes.client")
    system = Field("attributes.system")
    irc_nickname = Field("attributes.data.IRCNick", default=client)
    created_at = Field("attributes.createdAt", to_obj=str_to_datetime, to_json=datetime_to_str)
    updated_at = Field("attributes.updatedAt", to_obj=str_to_datetime, to_json=datetime_to_str)
    unidentified_rats = Field("attributes.unidentifiedRats")
    quotes = Field("attributes.quotes", to_obj=lambda quotes: list(map(QuotationConverter.to_obj, quotes)),
                 to_json=lambda quotes: list(map(QuotationConverter.to_json, quotes)))
    is_open = Field("attributes.status", to_obj=lambda status: status in ("open", "inactive"))
    epic = Field("relationships.epics.data", to_obj=lambda epics: len(epics) > 0, retention=Retention.MODEL_ONLY)
    title = Field("attributes.title")
    code_red = Field("attributes.codeRed")
    first_limpet = Field("attributes.firstLimpetId", to_obj=UUID, to_json=str)
    board_index = Field("attributes.data.boardIndex", default=None, optional=True)
    mark_for_deletion = Field("attributes.data.markedForDeletion")
    lang_id = Field("attributes.data.langID")
    rats = Field("relationships.rats.data")


class WebsocketAPIHandler20(WebsocketRequestHandler, APIHandler):
    """Handler for API version 2.0."""
    api_version = "v2.0"

    async def update_rescue(self, rescue, full: bool) -> Dict[str, Any]:
        """
        Send a rescue's data to the API.

        Arguments:
            rescue (Rescue): :class:`Rescue` object to be sent.
            full (bool): If this is True, all rescue data will be sent. Otherwise, only properties
                that have changed.

        Raises:
            ValueError: If *rescue* doesn't have its case ID set.
        """
        if rescue.case_id is None:
            raise ValueError("Cannot send rescue without ID to the API")
        else:
            return await self._request({"action": ("rescues", "update"),
                                        "id": rescue.case_id,
                                        "data": rescue.json(full)})

    async def get_rescues(self, **criteria) -> Set[Rescue]:
        """Get all rescues from the API matching the criteria provided."""
        data = await RescueConverter.to_search_parameters(criteria)
        data["action"] = ("rescues", "read")

        response = await self._request(data)

        results = set()
        for json_rescue in response["data"]:
            results.add(self.rescue_from_json(json_rescue))

        return results

    async def get_rescue_by_id(self, id: Union[str, UUID]) -> Rescue:
        """Get rescue with the provided ID."""
        return (await self.get_rescues(id=id)).pop()

    async def get_rats(self, **criteria) -> Set[Rats]:
        """Get all rats from the API matching the criteria provided."""
        data = self._make_serializable(criteria)
        data["action"] = ("rats", "read")

        response = await self._request(data)

        results = set()
        for json_rat in response["data"]:
            results.add(self.rat_from_json(json_rat))

        return results

    async def get_rat_by_id(self, id: Union[str, UUID]) -> Rats:
        """Get rat with the provided ID."""
        return (await self.get_rats(id=id)).pop()

    async def _handle_update(self, data: dict, event: str):
        """Handle an update from the API."""
        if event == "rescueUpdated":
            for rescue_json in data["data"]:
                self.board.from_api(self.rescue_from_json(rescue_json))

    @classmethod
    async def quotation_from_json(cls, json: dict) -> Quotation:
        """
        Take the JSON dict representing a case json (from !inject) as returned by the API and
        construct a :class:`Quotation` object from it.
        """
        return await QuotationConverter.to_obj(json)

    @classmethod
    async def rescue_from_json(cls, json: dict) -> Rescue:
        """
        Take the JSON dict representing a rescue as returned by the API and construct a
        :class:`Rescue` object from it.
        """

        if json["type"] == "rescues":
            return await RescueConverter.to_obj(json)
        else:
            raise ValueError("JSON dict does not seem to represent a rescue")

    @classmethod
    async def rat_from_json(cls, json: dict) -> Rats:
        if json["type"] != "rats":
            raise ValueError("JSON dict does not seem to represent a rat")

        return Rats(
            UUID(json["id"]),
            json["attributes"]["name"]
        )

    @classmethod
    def _make_serializable(cls, data: dict) -> dict:
        result = {}
        for key, value in data.items():
            if isinstance(value, UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                result[key] = value

        return result
