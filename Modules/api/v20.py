"""
exceptions.py - Handler(s) for API v2.0

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from datetime import datetime
from typing import Union, List

from uuid import UUID

from Modules.api.converter import Converter, Field, Retention
from Modules.rat_quotation import Quotation
from Modules.rat_rescue import Rescue
from Modules.rats import Rats
from utils.ratlib import Status, Platforms
from .api_handler import APIHandler
from .websocket import WebsocketRequestHandler


async def _rats_from_json(rats: List[dict]) -> List[Rats]:
    return [await Rats.get_rat_by_uuid(UUID(rat["id"])) for rat in rats]

async def _quotes_from_json(quotes: List[dict]) -> List[Quotation]:
    return [await QuotationConverter.to_obj(quote) for quote in quotes]

async def _quotes_to_json(quotes: List[Quotation]) -> List[dict]:
    return [await QuotationConverter.to_json(quote) for quote in quotes]


class RatsConverter(Converter, klass=Rats):
    uuid = Field("id", to_obj=UUID, to_json=str, criterion="id")
    name = Field("attributes.name", criterion="name")
    platform = Field("attributes.platform",
                     to_obj=lambda string: Platforms[string.upper()],
                     to_json=lambda platform: platform.name.lower(),
                     criterion="platform")

    @classmethod
    async def final_to_json(cls, json: dict):
        json["type"] = "rats"
        return json

class QuotationConverter(Converter, klass=Quotation):
    datetime_to_str = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
    str_to_datetime = lambda string: datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.%f")

    message = Field("message")
    author = Field("author")
    created_at = Field("createdAt", to_obj=str_to_datetime, to_json=datetime_to_str),
    updated_at = Field("updatedAt", to_obj=str_to_datetime, to_json=datetime_to_str),
    last_author = Field("lastAuthor")

class RescueConverter(Converter, klass=Rescue):
    datetime_to_str = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    str_to_datetime = lambda string: datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.%fZ")

    case_id = Field("id", to_obj=UUID, to_json=str, criterion="id")
    client = Field("attributes.client", criterion="client")
    system = Field("attributes.system", criterion="system")
    irc_nickname = Field("attributes.data.IRCNick", default=client, criterion="irc_nickname")
    created_at = Field("attributes.createdAt",
                       to_obj=str_to_datetime,
                       to_json=datetime_to_str,
                       criterion="created_at")
    updated_at = Field("attributes.updatedAt",
                       to_obj=str_to_datetime,
                       to_json=datetime_to_str,
                       criterion="updated_at")
    unidentified_rats = Field("attributes.unidentifiedRats")
    quotes = Field("attributes.quotes",
                   to_obj=_quotes_from_json,
                   to_json=_quotes_to_json)
    status = Field("attributes.status",
                   to_obj=lambda string: Status[string.upper()],
                   to_json=lambda status: status.name.lower(),
                   criterion="status")
    epic = Field("relationships.epics.data",
                 to_obj=lambda epics: len(epics) > 0,
                 retention=Retention.MODEL_ONLY)
    title = Field("attributes.title", criterion="title")
    code_red = Field("attributes.codeRed", criterion="code_red")
    first_limpet = Field("attributes.firstLimpetId", to_obj=UUID, to_json=str,
                         criterion="first_limpet")
    board_index = Field("attributes.data.boardIndex", default=None, criterion="board_index")
    mark_for_deletion = Field("attributes.data.markedForDeletion")
    lang_id = Field("attributes.data.langID", criterion="lang_id")
    rats = Field("relationships.rats.data",
                 to_obj=_rats_from_json,
                 to_json=lambda rats: [{"id": str(rat.uuid), "type": "rats"} for rat in rats])
    outcome = Field("attributes.outcome",
                    retention=Retention.JSON_ONLY,
                    criterion="outcome")

    @classmethod
    async def final_to_json(cls, json: dict):
        json["type"] = "rescues"
        return json


class WebsocketAPIHandler20(WebsocketRequestHandler, APIHandler):
    """Handler for API version 2.0."""
    api_version = "v2.0"

    async def update_rescue(self, rescue, full: bool=True):
        """
        Update a rescue's data in the API.

        Arguments:
            rescue (Rescue): Rescue to be updated in the API.
            full (bool): If this is True, all rescue data will be sent. Otherwise, only properties
                that have changed.

        Raises:
            ValueError: If *rescue* doesn't have its case ID set.
        """
        if rescue.case_id is None:
            raise ValueError("Cannot send rescue without ID to the API")
        else:
            await self._request({"action": ("rescues", "update"),
                                 "id": str(rescue.case_id),
                                 "data": await RescueConverter.to_json(rescue)})

    async def create_rescue(self, rescue: Rescue) -> UUID:
        """
        Create a rescue within the API.

        Raises:
            ValueError: If the provided rescue already has its ID set.
        """
        if rescue.case_id is None:
            response = await self._request({"action": ("rescues", "create"),
                                            "data": await RescueConverter.to_json(rescue)})
            # rescue.case_id = UUID(response["data"][0]["id"])
            return UUID(response["data"][0]["id"])
        else:
            raise ValueError("cannot send rescue which already has api id set")

    async def delete_rescue(self, rescue: Union[Rescue, UUID]):
        """
        Delete a rescue in the API.

        Arguments:
            rescue (Rescue or UUID): Rescue to delete. Can be either a UUID or a Rescue object.
                In the latter case, the rescue's ID must not be None.

        Raises:
            ValueError: If a Rescue object without its ID set was provided.
        """
        if isinstance(rescue, Rescue):
            if rescue.case_id is None:
                raise ValueError("cannot delete rescue without ID in the api")
            else:
                rescue = rescue.case_id

        response = await self._request({"action": ("rescues", "delete"),
                                        "id": str(rescue)})

    async def get_rescues(self, **criteria) -> List[Rescue]:
        """Get all rescues from the API matching the criteria provided."""
        data = await RescueConverter.to_search_parameters(criteria)
        data["action"] = ("rescues", "read")

        response = await self._request(data)

        results = []
        for json_rescue in response["data"]:
            results.append(await RescueConverter.to_obj(json_rescue))

        return results

    async def get_rescue_by_id(self, id: Union[str, UUID]) -> Rescue:
        """Get rescue with the provided ID."""
        return (await self.get_rescues(id=id))[0]

    async def get_rats(self, **criteria) -> List[Rats]:
        """Get all rats from the API matching the criteria provided."""
        data = await RatsConverter.to_search_parameters(criteria)
        data["action"] = ("rats", "read")

        response = await self._request(data)

        results = []
        for json_rat in response["data"]:
            results.append(await RatsConverter.to_obj(json_rat))

        return results

    async def get_rat_by_id(self, id: Union[str, UUID]) -> Rats:
        """Get rat with the provided ID."""
        return (await self.get_rats(id=id))[0]

    async def _handle_update(self, data: dict, event: str):
        """Handle an update from the API."""
        for rescue_json in data["data"]:
            rescue = await RescueConverter.to_obj(rescue_json)
            if event == "rescueUpdated":
                if rescue.open:
                    if rescue in self.board:
                        self.board.modify(rescue)
                    else:
                        self.board.append(rescue)
                else:
                    if rescue in self.board:
                        self.board.remove(rescue)
            elif event == "rescueCreated":
                if rescue.open and rescue not in self.board:
                    self.board.append(rescue)
            elif event == "rescueDeleted":
                if rescue in self.board:
                    self.board.remove(rescue)
