"""
v20.py - Handler(s) for API v2.0

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from operator import attrgetter
from datetime import datetime
from typing import Union, List
from functools import partial

from uuid import UUID

from Modules.api.search import Search
from Modules.api.versions import Version
from Modules.epic import Epic
from Modules.mark_for_deletion import MarkForDeletion
from Modules.rat_quotation import Quotation
from Modules.rat_rescue import Rescue
from Modules.rats import Rats
from utils.ratlib import Status, Platforms, Outcome
from .api_handler import APIHandler
from .websocket import WebsocketRequestHandler


class WebsocketAPIHandler20(WebsocketRequestHandler, APIHandler):
    """Handler for API version 2.0."""
    api_version: Version = Version.V_20
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._rescue_search = Search()
        self._rescue_search.add("id", "id", types=UUID, sanitize=str)
        self._rescue_search.add("client", "client", types=str),
        self._rescue_search.add("system", "system", types=str, sanitize=str.upper)
        self._rescue_search.add("status", "status", types=Status,
                                sanitize=lambda status: status.name.lower())
        self._rescue_search.add("unidentified_rats", "unidentifiedRats", types=list)
        self._rescue_search.add("created_at", "createdAt", types=datetime,
                                sanitize=partial(datetime.strftime, format="%Y-%m-%dT%H:%M:%S.%fZ"))
        self._rescue_search.add("updated_at", "updatedAt", types=datetime,
                                sanitize=partial(datetime.strftime, format="%Y-%m-%dT%H:%M:%S.%fZ"))
        self._rescue_search.add("quotes", "quotes", types=(list, Quotation),
                                sanitize=lambda quotes: [self._rescue_to_json(quote)
                                                         for quote in list(quotes)])
        self._rescue_search.add("title", "title", types=str, nullable=True)
        self._rescue_search.add("code_red", "codeRed", bool)
        self._rescue_search.add("first_limpet", "firstLimpetId", types=(Rats, UUID), nullable=True,
                                sanitize=lambda fl: str(fl if isinstance(fl, UUID) else fl.uuid))
        self._rescue_search.add("marked_for_deletion", "data.markedForDeletion.marked", types=bool)
        self._rescue_search.add("irc_nickname", "IRCNick", types=str)
        self._rescue_search.add("lang_id", "data.langID", types=str)
        self._rescue_search.add("outcome", "outcome", types=Outcome,
                                sanitize=attrgetter("value"))

        self._rat_search = Search()
        self._rat_search.add("id", "id", types=UUID, sanitize=str)
        self._rat_search.add("name", "name", types=str)
        self._rat_search.add("platform", "platform", types=Platforms,
                             sanitize=lambda platform: None if platform is Platforms.DEFAULT
                                                       else platform.name.lower())

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
        if rescue.uuid is None:
            raise ValueError("Cannot send rescue without ID to the API")
        else:
            await self._request({"action": ("rescues", "update"),
                                 "id": str(rescue.uuid),
                                 "data": self._rescue_to_json(rescue)})

    async def create_rescue(self, rescue: Rescue) -> UUID:
        """
        Create a rescue within the API.

        Raises:
            ValueError: If the provided rescue already has its ID set.
        """
        if rescue.uuid is None:
            response = await self._request({"action": ("rescues", "create"),
                                            "data": self._rescue_to_json(rescue)})
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
            if rescue.uuid is None:
                raise ValueError("cannot delete rescue without ID in the api")
            else:
                rescue = rescue.uuid

        await self._request({"action": ("rescues", "delete"),
                             "id": str(rescue)})

    async def get_rescues(self, **criteria) -> List[Rescue]:
        """Get all rescues from the API matching the criteria provided."""
        data = self._rescue_search.generate(criteria)
        data["action"] = ("rescues", "read")

        response = await self._request(data)

        results = []
        for json_rescue in response["data"]:
            results.append(await self._rescue_from_json(json_rescue))

        return results

    async def get_rescue_by_id(self, id: Union[str, UUID]) -> Rescue:
        """Get rescue with the provided ID."""
        return (await self.get_rescues(id=id))[0]

    async def get_rats(self, **criteria) -> List[Rats]:
        """Get all rats from the API matching the criteria provided."""
        data = self._rat_search.generate(criteria)
        data["action"] = ("rats", "read")

        response = await self._request(data)

        results = []
        for json_rat in response["data"]:
            results.append(self._rat_from_json(json_rat))

        return results

    async def get_rat_by_id(self, id: Union[str, UUID]) -> Rats:
        """Get rat with the provided ID."""
        return (await self.get_rats(id=id))[0]

    async def _handle_update(self, data: dict, event: str):
        """Handle an update from the API."""
        for rescue_json in data["data"]:
            rescue = await self._rescue_from_json(rescue_json)
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

    @classmethod
    def _quotation_from_json(cls, json: dict) -> Quotation:
        return Quotation(
            message=json["message"],
            created_at=datetime.strptime(json["createdAt"], "%Y-%m-%dT%H:%M:%S.%f"),
            updated_at=datetime.strptime(json["updatedAt"], "%Y-%m-%dT%H:%M:%S.%f"),
            author=json["author"],
            last_author=json["lastAuthor"]
        )

    @classmethod
    def _quotation_to_json(cls, quote: Quotation) -> dict:
        return {
            "message": quote.message,
            "createdAt": quote.created_at.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "updatedAt": quote.updated_at.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "author": quote.author,
            "lastAuthor": quote.last_author
        }

    @classmethod
    def _mfd_from_json(cls, json: dict) -> MarkForDeletion:
        if json.get("reporter", None) == "Noone.":
            json["reporter"] = None
        if json.get("reason", None) == "None.":
            json["reason"] = None

        return MarkForDeletion(**json)

    @classmethod
    def _mfd_to_json(cls, mfd: MarkForDeletion) -> dict:
        return {
            "marked": mfd.marked,
            "reporter": mfd.reporter,
            "reason": mfd.reason
        }

    @classmethod
    def _epic_from_json(cls, json: dict) -> Epic:
        return Epic(
            uuid=json["id"],
            notes=json["attributes"]["notes"],
            rescue=cls.board.find_by_uuid(UUID(json["attributes"]["rescueId"], 4)),
            rat=cls.board.find_by_uuid(UUID(json["attributes"]["ratId"], 4))
        )

    @classmethod
    async def _rescue_from_json(cls, json: dict) -> Rescue:
        result = Rescue(
            uuid=UUID(json["id"], version=4),
            client=json["attributes"]["client"],
            system=json["attributes"]["system"],
            irc_nickname=json["attributes"]["data"]
                .get("IRCNick", json["attributes"]["client"]),
            created_at=datetime.strptime(json["attributes"]["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            updated_at=datetime.strptime(json["attributes"]["updatedAt"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            unidentified_rats=json["attributes"]["unidentifiedRats"],
            quotes=list(map(cls._quotation_from_json, json["attributes"]["quotes"])),
            # epic=list(map(cls.)), TODO: Add getting epics
            title=json["attributes"]["title"],
            status=Status[json["attributes"]["status"].upper()],
            code_red=json["attributes"]["codeRed"],
            first_limpet=UUID(json["attributes"]["firstLimpetId"], version=4),
            board_index=json["attributes"].get("data", {}).get("boardIndex", None),
            mark_for_deletion=cls._mfd_from_json(json["attributes"].get("data", {})
                                                 .get("markedForDeletion", {})),
            lang_id=json["attributes"].get("data", {}).get("langID", "en"),
            rats=[await Rats.get_rat_by_uuid(UUID(rat["id"], version=4))
                  for rat in json["relationships"]["rats"]["data"]]
        )
        if json["attributes"]["platform"] is None:
            result.platform = Platforms.DEFAULT
        else:
            result.platform = Platforms[json["attributes"]["platform"].upper()]

        return result

    @classmethod
    def _rescue_to_json(cls, rescue: Rescue) -> dict:
        result = {
            "client": rescue.client,
            "system": rescue.system,
            "status": rescue.status.name.lower(),
            "unidentifiedRats": rescue.unidentified_rats,
            "createdAt": rescue.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "updatedAt": rescue.updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "quotes": list(map(cls._quotation_to_json, rescue.quotes)),
            "title": rescue.title,
            "codeRed": rescue.code_red,
            "firstLimpetId": str(rescue.first_limpet),
            "data": {
                "IRCNick": rescue.irc_nickname,
                "langID": rescue.lang_id.lower(),
                "markedForDeletion": cls._mfd_to_json(rescue.marked_for_deletion)
            }
        }
        if rescue.board_index is not None:
            result["data"]["boardIndex"] = rescue.board_index

        return result

    @classmethod
    def _rat_from_json(cls, json: dict):
        return Rats(
            uuid=UUID(json["id"], version=4),
            name=json["attributes"]["name"],
            platform=Platforms.DEFAULT if json["attributes"]["platform"] is None
                     else Platforms[json["attributes"]["platform"].upper()]
        )
