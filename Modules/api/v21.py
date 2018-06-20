"""
v21.py - Handler(s) for API v2.1

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from typing import Union, List

from uuid import UUID

from Modules.api.v20 import WebsocketAPIHandler20
from Modules.rat_rescue import Rescue
from Modules.rats import Rats


class WebsocketAPIHandler21(WebsocketAPIHandler20):
    """Handler for API version 2.1."""
    api_version = "v2.1"

    async def get_rescues(self, **criteria) -> List[Rescue]:
        """Get all rescues from the API matching the criteria provided."""
        data = self._rescue_search.generate(criteria)
        data["action"] = ("rescues", "search")

        response = await self._request(data)

        results = []
        for json_rescue in response["data"]:
            results.append(await self._rescue_from_json(json_rescue))

        return results

    async def get_rescue_by_id(self, id: Union[str, UUID]) -> Rescue:
        """Get rescue with the provided ID."""
        response = await self._request({
            "action": ("rescues", "read"),
            "id": str(id)
        })

        return await self._rescue_from_json(response["data"])

    async def get_rats(self, **criteria) -> List[Rats]:
        data = self._rat_search.generate(criteria)
        data["action"] = ("rats", "search")

        response = await self._request(data)

        results = []
        for json_rescue in response["data"]:
            results.append(self._rat_from_json(json_rescue))

        return results

    async def get_rat_by_id(self, id: Union[str, UUID]) -> Rats:
        response = await self._request({
            "action": ("rats", "read"),
            "id": str(id)
        })

        return self._rat_from_json(response["data"])
