"""
websocket.py - Provides facilities for handling requests etc. over a websocket connection.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
import asyncio
import json
import logging
from abc import abstractmethod
from json import JSONDecodeError
from typing import Set, Dict, Any, Union, Optional, List
from uuid import UUID, uuid4

import websockets

from Modules.api.api_handler import APIHandler
from Modules.api.versions import Version
from config import config
from utils.abstract import Abstract
from .exceptions import NotConnectedError, MismatchedVersionError, APIError, UnauthorizedError, \
    ForbiddenError, InternalAPIError

log = logging.getLogger(f"{config['logging']['base_logger']}.{__name__}")


class BaseWebsocketAPIHandler(APIHandler, Abstract):
    """
    Base class for API Handlers.
    Defines methods for requests and all that rubbish.
    """

    def __init__(self, hostname: str, token: str=None, tls=True, *,
                 loop: asyncio.BaseEventLoop=None,
                 connection: websockets.WebSocketClientProtocol=None):
        """
        Initialize a new API Handler.

        Arguments:
            hostname (str): Hostname to connect to.
            token (str): OAuth token to be used for authorization or None if it's not needed.
            tls (bool): Whether to use TLS when connecting or not ('ws:' versus 'wss:').
            loop (asyncio.BaseEventLoop): Custom event loop to use. Defaults to global loop.
            connection (websockets.WebSocketClientProtocol): Connection to use. If this is given,
                the handler will immediately be in a connected state. Overrides version checks.

        Raises:
            ValueError: When both *loop* and *connection* are provided but *connection* is not
                running in *loop*.
        """
        self._hostname = hostname
        self._token = token
        self._tls = tls

        if connection is None:
            if loop is None:
                self._loop = asyncio.get_event_loop()
            else:
                self._loop = loop
        else:
            if loop is None:
                self._loop = connection.loop
            else:
                if loop is connection.loop:
                    self._loop = loop
                else:
                    raise ValueError("conflicting arguments: cannot run in a different event loop from "
                                     "the connection")

        self._connection: websockets.WebSocketClientProtocol = connection

        if connection:
            self._listener_task: asyncio.Task = self._loop.create_task(self._message_handler())
        else:
            self._listener_task: asyncio.Task = None

        self._waiting_requests: Set[UUID] = set()
        """Holds UUIDs of requests currently waiting for a response."""
        self._request_responses: Dict[UUID, Dict[str, Any]] = {}
        """Maps request UUIDs to their responses. See :meth:`self._retrieve_response`"""

    connected: bool = property(lambda self: self._connection is not None and self._connection.open)

    hostname = property(lambda self: self._hostname)
    token = property(lambda self: self._token)
    tls = property(lambda self: self._tls)

    async def connect(self):
        """
        Connect to server, start the listener task and make sure we are on the correct API version.

        Raises:
            NotConnectedError: If this instance is already connected. Shush.
            MismatchedVersionError: If this handler version does not match that of the API we're
                connecting to.
            APIError: If the API sent rubbish as a connect message.
        """
        if self.connected:
            raise NotConnectedError(f"Already connected to a server: {self._connection.host}")

        uri = generate_ws_uri(self._hostname, token=self._token, tls=self._tls)
        self._connection = await websockets.connect(uri, loop=self._loop)

        # Grab the connect message and compare versions
        try:
            version = parse_connect_event(json.loads(await self._connection.recv()))
        except JSONDecodeError as de:
            raise APIError("connect message from the API could not be parsed") from de
        else:
            if version != self.api_version:
                await self._connection.close(reason="Mismatched version")
                raise MismatchedVersionError(self.api_version.value, version.value)

        self._listener_task = self._loop.create_task(self._message_handler())
        log.info(f"Connected to API at {uri}")

    async def disconnect(self):
        """
        Disconnect from the server.

        Raises:
            NotConnectedError: If this instance is not connected.
        """
        if not self.connected:
            raise NotConnectedError

        await self._connection.close()
        log.info("Disconnected from API")

    @abstractmethod
    async def _handle_update(self, data: dict, event: str):
        """Handle an update from the API."""

    @abstractmethod
    async def _cache_included(self, included: List[dict]):
        """Consume (most likely cache) objects that were included in an API response."""
        pass

    async def _message_handler(self):
        """
        Handler to be run continuously. Grabs messages from the connection, parses them and assigns
        them to the appropriate request.
        """
        while True:
            try:
                message = await self._connection.recv()
            except websockets.ConnectionClosed:
                return

            try:
                data: dict = json.loads(message)
            except json.JSONDecodeError:
                log.error(f"The following message from the API could not be parsed: {message}")
                continue

            if "included" in data.keys():
                await self._cache_included(data["included"])

            try:
                request_id = UUID(data["meta"]["request_id"])
            except KeyError:
                # no request_id in there
                if "code" in data.keys():
                    # API returned us an error code
                    if data["code"] == "unauthorized":
                        log.error("A recent request required an API token, but none is provided")
                    elif data["code"] == "forbidden":
                        log.error("A recent request required permissions we don't have")
                    elif data["code"] == "internal_server":
                        log.error("A recent request caused an internal API error")
                    else:
                        log.error(f"Received unknown error code '{data['code']}' from the API")
                elif "meta" in data.keys() and "event" in data["meta"].keys():
                    await self._handle_update(data, data["meta"]["event"])
                else:
                    log.error(f"Message from the API is not a response or update: {data}")
            except ValueError:
                # not a valid UUID
                log.error(f"Request ID in API message was not a valid UUID: "
                          f"{data['meta']['request_id']}")
            else:
                if request_id not in self._waiting_requests:
                    log.error(f"Received unexpected API response: {request_id}")
                else:
                    self._request_responses[request_id] = data
                    self._waiting_requests.remove(request_id)

    async def _send_raw(self, data: Union[str, bytes, dict]):
        """Send raw data to the server."""
        if not self.connected:
            raise NotConnectedError

        if isinstance(data, str) or isinstance(data, bytes):
            await self._connection.send(data)
        else:
            await self._connection.send(json.dumps(data))

    async def _request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the server, attaching a randomly generated UUID in order to identify and
        return the response.
        """
        request_id = uuid4()
        while request_id in self._waiting_requests or request_id in self._request_responses.keys():
            request_id = uuid4()

        if "meta" in data.keys():
            data["meta"]["request_id"] = str(request_id)
        else:
            data["meta"] = {"request_id": str(request_id)}

        log.debug(f"Sending request to {self.hostname}: {data}")
        self._waiting_requests.add(request_id)
        await self._send_raw(data)
        result = await self._retrieve_response(request_id)
        if "count" in result.setdefault("meta", {}).keys():
            log.debug(f"Received {result['meta']['count']} entries from the API")
        return result

    async def _retrieve_response(self, request_id: UUID, max_wait: int=600) -> Dict[str, Any]:
        """
        Wait for a response to a particular request and return it. Responses are provided in
        :field:`self._request_responses` by :meth:`self._message_handler`.

        Arguments:
            request_id (UUID): The request's ID which was included in the sent metadata and will be
                returned untouched by the API.
            max_wait (int): Abort after this amount of time. In hundredths of a second.

        Raises:
            TimeoutError: If the API takes longer than *max_wait* to respond.
            APIError: If no request with *request_id* was ever made or the response was consumed by
                something else, neither of which should happen.
        """
        if request_id not in self._waiting_requests and \
                request_id not in self._request_responses.keys():
            raise APIError(f"Response to request {request_id} already consumed or request never "
                           f"queued")

        for i in range(max_wait):
            if request_id in self._waiting_requests:
                await asyncio.sleep(0.01)
            else:
                break
        else:
            self._waiting_requests.remove(request_id)
            raise TimeoutError(f"API took too long to respond to request {request_id}")

        try:
            response = self._request_responses.pop(request_id)
        except KeyError:
            raise APIError(f"Response to request {request_id} not available")

        if "code" in response.keys():
            # API returned us an error code
            if response["code"] == "unauthorized":
                raise UnauthorizedError
            elif response["code"] == "forbidden":
                raise ForbiddenError
            elif response["code"] == "internal_server":
                raise InternalAPIError
            else:
                log.error(f"Received unknown error code '{response['code']}' from the API")
        else:
            return response


def generate_ws_uri(hostname: str, path: str= "/", token: str=None, tls=True) -> str:
    """
    Get the URI for the specified parts.

    Args:
        hostname (str): DNS hostname or IP address of the target.
        path (str): Path on the target. Defaults to `/`.
        token (str): Token to provide on connection via query parameter (`?bearer=my-token`)
        tls (bool): Whether to connect using TLS / SSL.

    Returns:
        str: Complete URI of the pattern '`ws(s)://<hostname>/<path>?bearer=<token>`' containing the
            provided parts.
    """
    uri = f"wss://{hostname}{path}" if tls else f"ws://{hostname}{path}"
    if token:
        uri += f"?bearer={token}"
    return uri


def parse_connect_event(message: dict) -> Optional[Version]:
    """Parses the connect event message from the API and returns the version of the API"""
    if "meta" in message.keys() and "API-Version" in message["meta"].keys():
        return Version(message["meta"]["API-Version"])
    else:
        log.warning("Did not receive version field from API")
        return None
