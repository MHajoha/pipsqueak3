from typing import Tuple, Union
from uuid import UUID

import datetime
import pytest

from Modules.api import WebsocketAPIHandler20, WebsocketAPIHandler21
from Modules.api.search import Not, In
from Modules.rat_rescue import Rescue
from Modules.rats import Rats
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
                           rescue_fx: Tuple[dict, Rescue],
                           criteria: dict, expected_request: dict):
    handler, connection = handler_fx
    json_rescue, rescue = rescue_fx

    connection.response = add_meta([json_rescue])
    result = await handler.get_rescues(**criteria)

    assert connection.was_sent({
        "action": ["rescues", "read" if type(handler) is WebsocketAPIHandler20 else "search"],
        **expected_request
    })

    assert len(result) == 1
    assert result[0] == rescue


@pytest.mark.parametrize("criteria,expected_request", [
    ({"name": "MrRatMan", "platform": Platforms.PC},
     {"name": "MrRatMan", "platform": "pc"})
])
@pytest.mark.asyncio
async def test_get_rats(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                        rats_fx: Tuple[dict, Rats],
                        criteria: dict, expected_request: dict):
    handler, connection = handler_fx
    json_rat, rat = rats_fx

    connection.response = add_meta([json_rat])
    result = await handler.get_rats(**criteria)

    assert connection.was_sent({
        "action": ["rats", "read" if type(handler) is WebsocketAPIHandler20 else "search"],
        **expected_request
    })

    assert len(result) == 1
    assert result[0] == rat


@pytest.mark.asyncio
async def test_get_rescue_by_id(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                                rescue_fx: Tuple[dict, Rescue]):
    handler, connection = handler_fx
    json_rescue, rescue = rescue_fx

    connection.response = add_meta(json_rescue if type(handler) is WebsocketAPIHandler21
                                   else [json_rescue])
    result = await handler.get_rescue_by_id(
        UUID("bede70e3-a695-448a-8376-ecbcf74385b6"))

    assert connection.was_sent({
        "action": ["rescues", "read"],
        "id": "bede70e3-a695-448a-8376-ecbcf74385b6"
    })

    assert result == rescue


@pytest.mark.asyncio
async def test_get_rat_by_id(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                             rats_fx: Tuple[dict, Rats]):
    handler, connection = handler_fx
    json_rat, rat = rats_fx

    connection.response = add_meta(json_rat if type(handler) is WebsocketAPIHandler21
                                   else [json_rat])
    result = await handler.get_rat_by_id(
        UUID("bede70e3-a695-448a-8376-ecbcf74385b6"))

    assert connection.was_sent({
        "action": ["rats", "read"],
        "id": "bede70e3-a695-448a-8376-ecbcf74385b6"
    })

    assert result == rat

@pytest.mark.asyncio
async def test_update_rescue(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                             rescue_fx: Tuple[dict, Rescue]):
    handler, connection = handler_fx
    json_rescue, rescue = rescue_fx

    connection.response = {"the api handler": "is going to ignore this"}
    await handler.update_rescue(rescue)

    json_rescue["attributes"].pop("notes")
    json_rescue["attributes"].pop("outcome")

    assert connection.was_sent({
        "action": ["rescues", "update"],
        "id": str(rescue.uuid),
        "data": json_rescue["attributes"]
    })
