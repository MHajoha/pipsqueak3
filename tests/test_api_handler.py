from typing import Tuple, Awaitable
from uuid import UUID

import asyncio
import pytest

from Modules.api import WebsocketAPIHandler20, WebsocketAPIHandler21
from Modules.rat_rescue import Rescue
from tests.mock_connection import MockWebsocketConnection


async def run_api_sync(handler: WebsocketAPIHandler20, coro: Awaitable):
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

    if type(handler) is WebsocketAPIHandler20:
        assert connection.was_sent({"action": ["rescues", "read"],
                                    "client": "Some Client",
                                    "firstLimpetId": "dc9c91fb-9ead-47e9-8771-81da2c1971bc"})
    elif type(handler) is WebsocketAPIHandler21:
        assert connection.was_sent({"action": ["rescues", "search"],
                                    "client": "Some Client",
                                    "firstLimpetId": "dc9c91fb-9ead-47e9-8771-81da2c1971bc"})

    assert len(result) == 1
    assert result.pop() == rescue
