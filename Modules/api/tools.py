import json
import logging
import websockets

from Modules.api.api_handler import APIHandler
from Modules.api.v20 import WebsocketAPIHandler20
from Modules.api.v21 import WebsocketAPIHandler21
from Modules.api.versions import Version
from Modules.api.websocket import generate_ws_uri, parse_connect_event
from config import config

log = logging.getLogger(f"{config['logging']['base_logger']}.{__name__}")

_handlers = {
    Version.V_20: WebsocketAPIHandler20,
    Version.V_21: WebsocketAPIHandler21
}


async def get_correct_version_handler(hostname: str, token: str=None, tls=True) -> APIHandler:
    """
    Get the correct handler for the API version which the hostname provided is running.
    The returned handler will already be connected.

    Arguments:
        hostname (str): Hostname to connect to.
        token (str): OAuth token to be used for authorization or None if it's not needed.
        tls (bool): Whether to use TLS when connecting or not.

    Raises:
        ValueError: If no appropriate handler can be found.
    """
    uri = generate_ws_uri(hostname, token=token, tls=tls)
    connection = await websockets.connect(uri)
    version = parse_connect_event(json.loads(await connection.recv()))

    if version in _handlers.keys():
        return _handlers[version](hostname, token, tls, connection=connection)
    else:
        raise ValueError(f"no handler found for API at {uri}")
