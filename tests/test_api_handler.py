from typing import Tuple, Union
from uuid import UUID

import datetime
import pytest

from Modules.api.api_handler import APIHandler
from Modules.api.search import Not, In
from Modules.api.tools import get_correct_version_handler
from Modules.api.versions import Version
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
async def test_get_rescues(handler_fx: Tuple[APIHandler, MockWebsocketConnection],
                           rescue_fx: RescueJSONTuple,
                           criteria: dict, expected_request: dict):
    handler, connection = handler_fx

    connection.responses.append(add_meta([rescue_fx.json_rescue]))
    for rat_tuple in rescue_fx.assigned_rats:
        connection.responses.append(add_meta(rat_tuple.json_rat))
    result = await handler.get_rescues(**criteria)

    assert connection.was_sent({
        "action": ["rescues", "search"],
        **expected_request
    })

    assert len(result) == 1
    assert result[0] == rescue_fx.rescue


@pytest.mark.asyncio
async def test_included_data(handler_fx: Tuple[APIHandler, MockWebsocketConnection],
                             rescue_fx: RescueJSONTuple):
    handler, connection = handler_fx

    connection.responses.append({
        "included": [rat_tuple.json_rat for rat_tuple in rescue_fx.assigned_rats],
        **add_meta([rescue_fx.json_rescue])
    })
    result = await handler.get_rescues(id=rescue_fx.rescue.uuid)

    assert len(
        connection.sent_messages) == 1  # ensure that no extra request was made to get the rat
    assert len(result) == 1
    assert result[0] == rescue_fx.rescue


@pytest.mark.parametrize("criteria,expected_request", [
    ({"name": "MrRatMan", "platform": Platforms.PC},
     {"name": "MrRatMan", "platform": "pc"})
])
@pytest.mark.asyncio
async def test_get_rats(handler_fx: Tuple[APIHandler, MockWebsocketConnection],
                        rats_fx: RatJSONTuple,
                        criteria: dict, expected_request: dict):
    handler, connection = handler_fx

    connection.responses.append(add_meta([rats_fx.json_rat]))
    result = await handler.get_rats(**criteria)

    assert connection.was_sent({
        "action": ["rats", "search"],
        **expected_request
    })

    assert len(result) == 1
    assert result[0] == rats_fx.rat


@pytest.mark.asyncio
async def test_get_rescue_by_id(handler_fx: Tuple[APIHandler, MockWebsocketConnection],
                                rescue_fx: RescueJSONTuple):
    handler, connection = handler_fx

    connection.responses.append(add_meta(rescue_fx.json_rescue))
    for rat_tuple in rescue_fx.assigned_rats:
        connection.responses.append(add_meta(rat_tuple.json_rat))
    result = await handler.get_rescue_by_id(
        UUID("bede70e3-a695-448a-8376-ecbcf74385b6"))

    assert connection.was_sent({
        "action": ["rescues", "read"],
        "id": "bede70e3-a695-448a-8376-ecbcf74385b6"
    })

    assert result == rescue_fx.rescue


@pytest.mark.asyncio
async def test_get_rat_by_id(handler_fx: Tuple[APIHandler, MockWebsocketConnection],
                             rats_fx: RatJSONTuple):
    handler, connection = handler_fx

    connection.responses.append(add_meta(rats_fx.json_rat))
    result = await handler.get_rat_by_id(
        UUID("bede70e3-a695-448a-8376-ecbcf74385b6"))

    assert connection.was_sent({
        "action": ["rats", "read"],
        "id": "bede70e3-a695-448a-8376-ecbcf74385b6"
    })

    assert result == rats_fx.rat


@pytest.mark.asyncio
async def test_update_rescue(handler_fx: Tuple[APIHandler, MockWebsocketConnection],
                             rescue_fx: RescueJSONTuple):
    handler, connection = handler_fx

    connection.responses.append(add_meta([rescue_fx.json_rescue]))
    for rat_tuple in rescue_fx.assigned_rats:
        connection.responses.append(add_meta(rat_tuple.json_rat))

    new_rescue = await handler.update_rescue(rescue_fx.rescue)

    rescue_fx.json_rescue["attributes"].pop("notes")
    rescue_fx.json_rescue["attributes"].pop("outcome")

    assert connection.was_sent({
        "action": ["rescues", "update"],
        "id": str(rescue_fx.rescue.uuid),
        "data": rescue_fx.json_rescue["attributes"]
    })

    assert new_rescue == rescue_fx.rescue


@pytest.mark.asyncio
async def test_create_rescue(handler_fx: Tuple[APIHandler, MockWebsocketConnection],
                             rescue_fx: RescueJSONTuple):
    handler, connection = handler_fx
    id = rescue_fx.rescue.uuid
    rescue_fx.rescue._id = None

    connection.responses.append(add_meta(rescue_fx.json_rescue))
    for rat_tuple in rescue_fx.assigned_rats:
        connection.responses.append(add_meta(rat_tuple.json_rat))

    new_rescue = await handler.create_rescue(rescue_fx.rescue)

    assert new_rescue.uuid == id == rescue_fx.rescue.uuid
    assert new_rescue == rescue_fx.rescue


@pytest.mark.parametrize("version", Version)
@pytest.mark.asyncio
async def test_get_correct_version_handler(connection_fx: MockWebsocketConnection,
                                           version: Version):
    connection_fx.incoming_messages.append({
        "meta": {
            "API-Version": version.value
        }
    })

    handler = await get_correct_version_handler("some_hostname")

    assert handler.api_version is version
    assert handler.connected
