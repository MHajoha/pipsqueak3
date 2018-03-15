"""
exceptions.py - Handler(s) for API v2.1

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from typing import Set, Union

from Modules.rat_rescue import Rescue, Quotation, Rats
from uuid import UUID

from Modules.api.v20 import WebsocketAPIHandler20


class WebsocketAPIHandler21(WebsocketAPIHandler20):
    """Handler for API version 2.1."""
    api_version = "v2.1"

    async def get_rescues(self, **criteria) -> Set[Rescue]:
        """Get all rescues from the API matching the criteria provided."""
        data = self._make_serializable(criteria)
        data["action"] = ("rescues", "search")

        response = await self._request(data)

        results = set()
        for json_rescue in response["data"]:
            results.add(self.rescue_from_json(json_rescue))

        return results

    async def get_rescue_by_id(self, id: Union[str, UUID]) -> Rescue:
        """Get rescue with the provided ID."""
        response = await self._request({
            "action": ("rescues", "read"),
            "id": str(id)
        })

        return self.rescue_from_json(response["data"][0])

    async def get_rats(self, **criteria) -> Set[Rats]:
        data = self._make_serializable(criteria)
        data["action"] = ("rats", "search")

        response = await self._request(data)

        results = set()
        for json_rescue in response["data"]:
            results.add(self.rescue_from_json(json_rescue))

        return results

    async def get_rat_by_id(self, id: Union[str, UUID]) -> Rats:
        response = await self._request({
            "action": ("rats", "read"),
            "id": str(id)
        })

        return self.rat_from_json(response["data"][0])
