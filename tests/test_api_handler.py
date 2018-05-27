from typing import Tuple, Awaitable
from uuid import UUID

import asyncio
import pytest

from Modules.api import WebsocketAPIHandler20, WebsocketAPIHandler21
from Modules.rat_rescue import Rescue
from Modules.rats import Rats
from ratlib.names import Platforms
from tests.mock_connection import MockWebsocketConnection


async def run_api_sync(handler: WebsocketAPIHandler20, coro: Awaitable):
    """
    This abomination is necessary because pytest (and probably unittest as well) won't run the
    listener task scheduled by the API handler.
    """
    return (await asyncio.wait(
        {
            coro,
            handler._message_handler(),
        },
        return_when=asyncio.FIRST_COMPLETED
    ))[0].pop().result()


@pytest.mark.asyncio
async def test_get_rescues(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                           rescue_fx: Tuple[dict, Rescue]):
    handler, connection = handler_fx
    json_rescue, rescue = rescue_fx

    await handler.connect()
    connection.response = json_rescue
    result = await run_api_sync(handler,
                                handler.get_rescues(client="Some Client",
                                first_limpet=UUID("dc9c91fb-9ead-47e9-8771-81da2c1971bc")))

    assert connection.was_sent(
        {
            "action": ["rescues", "read" if type(handler) is WebsocketAPIHandler20 else "search"],
            "client": "Some Client",
            "firstLimpetId": "dc9c91fb-9ead-47e9-8771-81da2c1971bc"
        }
    )

    assert len(result) == 1
    assert result.pop() == rescue


@pytest.mark.asyncio
async def test_get_rats(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                        rats_fx: Tuple[dict, Rats]):
    handler, connection = handler_fx
    json_rat, rat = rats_fx

    await handler.connect()
    connection.response = json_rat
    result = await run_api_sync(handler, handler.get_rats(name="MrRatMan", platform=Platforms.PC))

    assert connection.was_sent(
        {
            "action": ["rats", "read" if type(handler) is WebsocketAPIHandler20 else "search"],
            "name": "MrRatMan",
            "platform": "pc"
        }
    )

    assert len(result) == 1
    assert result.pop() == rat


@pytest.mark.asyncio
async def test_get_rescue_by_id(handler_fx: Tuple[WebsocketAPIHandler20, MockWebsocketConnection],
                                rescue_fx: Tuple[dict, Rescue]):
    handler, connection = handler_fx
    json_rescue, rescue = rescue_fx

    await handler.connect()
    connection.response = json_rescue
    result = await run_api_sync(handler, handler.get_rescue_by_id(
        UUID("bede70e3-a695-448a-8376-ecbcf74385b6")))

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

    await handler.connect()
    connection.response = json_rat
    result = await run_api_sync(handler, handler.get_rat_by_id(
        UUID("bede70e3-a695-448a-8376-ecbcf74385b6")))

    assert connection.was_sent({
        "action": ["rats", "read"],
        "id": "bede70e3-a695-448a-8376-ecbcf74385b6"
    })

    assert result == rat
