import asyncio
import json

from Modules.api import WebsocketAPIHandler20


class MockWebsocketConnection(object):
    """Fake websocket connection object to be used with the below convenience functions."""

    def __init__(self, handler_instance: WebsocketAPIHandler20):
        super().__init__()
        self.sent_messages = []
        self.incoming_messages = []
        self.response: dict = None
        self.handler = handler_instance

        self.host = "some_host"
        self.open = True

    async def send(self, data: dict):
        self.sent_messages.append(data)
        if self.response:
            try:
                data.setdefault("meta", {})["request_id"] = next(iter(
                    self.handler._waiting_requests
                ))
            except KeyError:
                pass
            else:
                self.incoming_messages.append(data)
                self.response = None

    async def recv(self):
        while len(self.incoming_messages) == 0:
            await asyncio.sleep(0.1)

        return json.dumps(self.incoming_messages.pop(0))

    async def close(self, reason):
        self.open = False

    def was_sent(self, data: dict) -> bool:
        """
        Checks if the specified dict was sent (meta field will be excluded for comparison) and
        removes it from the record if so.
        """
        for i, message in enumerate(self.sent_messages):
            try:
                message.pop("meta")
            except KeyError:
                pass

            try:
                data.pop("meta")
            except KeyError:
                pass

            if data == message:
                self.sent_messages.pop(i)
                return True
        else:
            return False