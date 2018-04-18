import asyncio
import pytest
import websockets
import json

from Modules.api.v20 import WebsocketAPIHandler20
from Modules.api.v21 import WebsocketAPIHandler21

@pytest.fixture(params=[WebsocketAPIHandler20, WebsocketAPIHandler21])
def handler(request):
    class MockWebsocketConnection(object):
        host = ""

        def __init__(self):
            super().__init__()
            self.sent_messages = []
            self.incoming_messages = []

        async def recv(self):
            while len(self.incoming_messages) == 0:
                await asyncio.sleep(0.1)

            return json.dumps(self.incoming_messages.pop(0))



    original_connect = websockets.connect
    websockets.connect = lambda *args, **kwargs: MockWebsocketConnection()

    instance = request.param("some_hostname", "some_token", "tls_or_not")

    def was_sent(data: dict) -> bool:
        """
        Checks if the specified dict was sent (meta field will be excluded for comparison) and
        removes it from the record if so.
        """
        for i, message in enumerate(instance._connection.sent_messages):
            try:
                message.pop("meta")
            except KeyError:
                pass

            try:
                data.pop("meta")
            except KeyError:
                pass

            if data == message:
                instance._connection.sent_messages.pop(i)
                return True
        else:
            return False


    def respond(data: dict):
        """
        Queues the provided dict as a response to a previously made request. Only works when only
        one request is waiting for a response.

        Raises:
             RuntimeError: If the above condition is not met.
        """
        if len(instance._waiting_requests) != 1:
            raise RuntimeError
        else:
            instance._connection.incoming_messages.append(
                {
                    "meta": {
                        "request_id": instance._waiting_requests.pop()
                    }
                }.update(data)
            )

    yield instance, was_sent, respond

    websockets.connect = original_connect
