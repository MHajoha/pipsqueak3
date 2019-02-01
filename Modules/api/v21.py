"""
v21.py - Handler(s) for API v2.1

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
import logging
from typing import Union, List

from uuid import UUID

from Modules.api.v20 import WebsocketAPIHandler20
from Modules.api.versions import Version
from Modules.rat_rescue import Rescue
from Modules.rat import Rat
from config import config
from utils.typechecking import check_type

log = logging.getLogger(f"{config['logging']['base_logger']}.{__name__}")


class WebsocketAPIHandler21(WebsocketAPIHandler20):
    """Handler for API version 2.1."""
    api_version: Version = Version.V_21

    async def get_rescues(self, **criteria) -> List[Rescue]:
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
        check_type(response["data"], list)
        if len(response["data"]) != 1:
            log.error(f"Expected API to return exactly one rescue, got {len(response)}.")

        return await self._rescue_from_json(response["data"][0])

    async def get_rats(self, **criteria) -> List[Rat]:
        data = self._rat_search.generate(criteria)
        data["action"] = ("rats", "search")

        response = await self._request(data)

        results = []
        for json_rescue in response["data"]:
            results.append(self._rat_from_json(json_rescue))

        return results

    async def get_rat_by_id(self, id: Union[str, UUID]) -> Rat:
        response = await self._request({
            "action": ("rats", "read"),
            "id": str(id)
        })
        check_type(response["data"], list)
        if len(response["data"]) != 1:
            log.error(f"Expected API to return exactly one rat, got {len(response)}.")

        return self._rat_from_json(response["data"][0])
