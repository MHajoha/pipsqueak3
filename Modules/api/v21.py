"""
exceptions.py - Handler(s) for API v2.1

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from typing import Union, List

from uuid import UUID

from Modules.api.v20 import WebsocketAPIHandler20, RescueConverter, RatsConverter
from Modules.rat_rescue import Rescue
from Modules.rats import Rats


class WebsocketAPIHandler21(WebsocketAPIHandler20):
    """Handler for API version 2.1."""
    api_version = "v2.1"

    async def get_rescues(self, **criteria) -> List[Rescue]:
        """Get all rescues from the API matching the criteria provided."""
        data = await RescueConverter.to_search_parameters(criteria)
        data["action"] = ("rescues", "search")

        response = await self._request(data)

        results = []
        for json_rescue in response["data"]:
            results.append(await RescueConverter.to_obj(json_rescue))

        return results

    async def get_rescue_by_id(self, id: Union[str, UUID]) -> Rescue:
        """Get rescue with the provided ID."""
        response = await self._request({
            "action": ("rescues", "read"),
            "id": str(id)
        })

        return await RescueConverter.to_obj(response["data"][0])

    async def get_rats(self, **criteria) -> List[Rats]:
        data = await RatsConverter.to_search_parameters(criteria)
        data["action"] = ("rats", "search")

        response = await self._request(data)

        results = []
        for json_rescue in response["data"]:
            results.append(await RatsConverter.to_obj(json_rescue))

        return results

    async def get_rat_by_id(self, id: Union[str, UUID]) -> Rats:
        response = await self._request({
            "action": ("rats", "read"),
            "id": str(id)
        })

        return await RatsConverter.to_obj(response["data"][0])
