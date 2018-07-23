from typing import Tuple, Union
from uuid import UUID

import datetime
import pytest

from Modules.api.search import Not, In
from Modules.api.v20 import WebsocketAPIHandler20
from Modules.api.v21 import WebsocketAPIHandler21
from Modules.rat_rescue import Rescue
from Modules.rat import Rat
from tests.testdata.rat1 import RatJSONTuple
from tests.testdata.rescue1 import RescueJSONTuple
from utils.ratlib import Platforms, Status
from tests.mock_connection import MockWebsocketConnection


def add_meta(data: Union[dict, list]) -> dict:
    return {
        "meta": {
            "count": 1,
            "limit": 25,
            "offset": 0,
            "total": 1
        },
        "data": data
    }


@pytest.mark.parametrize("criteria,expected_request", [
    ({"client": "Some Client", "first_limpet": UUID("dc9c91fb-9ead-47e9-8771-81da2c1971bc")},
     {"client": "Some Client", "firstLimpetId": "dc9c91fb-9ead-47e9-8771-81da2c1971bc"}),
    ({"updated_at": datetime.datetime(938, 3, 20, 4, 20, 0, 0)},
     {"updatedAt": "938-03-20T04:20:00.000000Z"}),
    ({"outcome": Not(None)},
     {"outcome": {"$not": None}}),
    ({"status": In(Status.OPEN, Status.CLOSED)},
     {"status": {"$in": ["open", "closed"]}})
])
@pytest.mark.asyncio
async def test_get_rescues(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                           rescue_fx: RescueJSONTuple,
                           criteria: dict, expected_request: dict):
    handler, connection = handler_fx

    connection.response = add_meta([rescue_fx.json_rescue])
    result = await handler.get_rescues(**criteria)

    assert connection.was_sent({
        "action": ["rescues", "read" if type(handler) is WebsocketAPIHandler20 else "search"],
        **expected_request
    })

    assert len(result) == 1
    assert result[0] == rescue_fx.rescue


@pytest.mark.parametrize("criteria,expected_request", [
    ({"name": "MrRatMan", "platform": Platforms.PC},
     {"name": "MrRatMan", "platform": "pc"})
])
@pytest.mark.asyncio
async def test_get_rats(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                        rats_fx: RatJSONTuple,
                        criteria: dict, expected_request: dict):
    handler, connection = handler_fx

    connection.response = add_meta([rats_fx.json_rat])
    result = await handler.get_rats(**criteria)

    assert connection.was_sent({
        "action": ["rats", "read" if type(handler) is WebsocketAPIHandler20 else "search"],
        **expected_request
    })

    assert len(result) == 1
    assert result[0] == rats_fx.rat


@pytest.mark.asyncio
async def test_get_rescue_by_id(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                                rescue_fx: RescueJSONTuple):
    handler, connection = handler_fx

    connection.response = add_meta(rescue_fx.json_rescue if type(handler) is WebsocketAPIHandler21
                                   else [rescue_fx.json_rescue])
    result = await handler.get_rescue_by_id(
        UUID("bede70e3-a695-448a-8376-ecbcf74385b6"))

    assert connection.was_sent({
        "action": ["rescues", "read"],
        "id": "bede70e3-a695-448a-8376-ecbcf74385b6"
    })

    assert result == rescue_fx.rescue


@pytest.mark.asyncio
async def test_get_rat_by_id(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                             rats_fx: RatJSONTuple):
    handler, connection = handler_fx

    connection.response = add_meta(rats_fx.json_rat if type(handler) is WebsocketAPIHandler21
                                   else [rats_fx.json_rat])
    result = await handler.get_rat_by_id(
        UUID("bede70e3-a695-448a-8376-ecbcf74385b6"))

    assert connection.was_sent({
        "action": ["rats", "read"],
        "id": "bede70e3-a695-448a-8376-ecbcf74385b6"
    })

    assert result == rats_fx.rat


@pytest.mark.asyncio
async def test_update_rescue(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                             rescue_fx: RescueJSONTuple):
    handler, connection = handler_fx

    connection.response = {"the api handler": "is going to ignore this"}
    await handler.update_rescue(rescue_fx.rescue)

    rescue_fx.json_rescue["attributes"].pop("notes")
    rescue_fx.json_rescue["attributes"].pop("outcome")

    assert connection.was_sent({
        "action": ["rescues", "update"],
        "id": str(rescue_fx.rescue.uuid),
        "data": rescue_fx.json_rescue["attributes"]
    })
