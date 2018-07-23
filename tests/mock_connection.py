import asyncio
import json
from typing import Union, List
from uuid import UUID

from Modules.api.v20 import WebsocketAPIHandler20


class MockWebsocketConnection(object):
    """Fake websocket connection object to be used with the below convenience functions."""

    def __init__(self, handler_instance: WebsocketAPIHandler20):
        super().__init__()
        self.sent_messages = []
        self.incoming_messages = []
        self.responses: List[dict] = []
        self.handler = handler_instance

        self.host = "some_host"
        self.open = True

    async def send(self, data: Union[str, dict]):
        if isinstance(data, str):
            data = json.loads(data)

        self.sent_messages.append(data)
        if len(self.responses) > 0:
            response = self.responses.pop(0)
            try:
                response.setdefault("meta", {})["request_id"] = next(iter(
                    self.handler._waiting_requests
                ))
            except StopIteration:
                pass  # No waiting requests
            else:
                self.incoming_messages.append(response)

    async def recv(self):
        while len(self.incoming_messages) == 0:
            await asyncio.sleep(0.1)

        message = self._make_serializable(self.incoming_messages.pop(0))
        return json.dumps(message)

    def _make_serializable(self, what: dict) -> dict:
        result = {}
        for key, value in what.items():
            if isinstance(value, UUID):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = self._make_serializable(value)
            else:
                result[key] = value
        return result

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