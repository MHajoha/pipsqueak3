"""
conftest.py - PyTest configuration and shared resources

Reusable test fixtures 'n stuff


Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE
"""
import logging
import asyncio
import json
import random
import string
import sys
from uuid import uuid4, UUID

import psycopg2
import psycopg2.pool
import websockets
import pytest

# from psycopg2.pool import SimpleConnectionPool

from Modules.rat_cache import RatCache

# Set argv to keep cli arguments meant for pytest from polluting our things

sys.argv = ["test",
            "--config-file", "testing.json",
            "--clean-log",
            "--verbose",
            ]

# This import statement is where the config gets read
from config import setup_logging

setup_logging("logs/unit_tests.log")

from Modules.permissions import Permission
from tests.mock_bot import MockBot
from Modules.api import WebsocketAPIHandler20, WebsocketAPIHandler21
from Modules.rat_board import RatBoard
from Modules.rat_rescue import Rescue
from Modules.rat import Rat
from utils.ratlib import Platforms
from Modules.context import Context
from Modules.epic import Epic
from Modules.user import User
from Modules.mark_for_deletion import MarkForDeletion
from tests.mock_callables import CallableMock, AsyncCallableMock
from database import DatabaseManager
from Modules.fact import Fact


@pytest.fixture(params=[("pcClient", Platforms.PC, "firestone", 24),
                        ("xxXclient", Platforms.XB, "sol", 2),
                        ("psCoolKid", Platforms.PS, "NLTT 48288", 33)],
                )
def rescue_sop_fx(request) -> Rescue:
    """
    A Rescue fixture providing Rescue objects for the 3 supported platforms

    Args:
        request (): Provided by fixture Parametrization

    Returns:
        Rescue : Rescue objects
    """
    params = request.param
    myRescue = Rescue(uuid4(), client=params[0], system=params[2], irc_nickname=params[0],
                      board_index=params[3])
    myRescue.platform = params[1]
    return myRescue


@pytest.fixture
def rescue_plain_fx() -> Rescue:
    """
    A plain initialized Rescue without parametrization

    Returns:
        Rescue : Plain initialized Rescue
    """
    return Rescue(uuid4(), "UNIT_TEST", "ki", "UNIT_TEST", board_index=42)


@pytest.fixture
def rat_no_id_fx():
    """
    Returns: (Rescue): Rescue test fixture without an api ID

    """
    return Rat(None, "noIdRat")


@pytest.fixture(params=[("myPcRat", Platforms.PC, UUID("dead4ac0-0000-0000-0000-00000000beef")),
                        ("someXrat", Platforms.XB, UUID("FEED000-FAC1-0000-0000900000D15EA5E")),
                        ("psRatToTheRescue", Platforms.PS,
                         UUID("FEE1DEA-DFAC-0000-000001BADB001FEED"))],
                )
def rat_good_fx(request) -> Rat:
    """
    Testing fixture containing good and registered rats
    """
    params = request.param
    myRat = Rat(params[2], name=params[0], platform=params[1])
    return myRat


@pytest.fixture
def rat_board_fx() -> RatBoard:
    """
    Provides a RatBoard object

    Returns:
        RatBoard: initialized ratboard object
    """
    return RatBoard()


@pytest.fixture
def bot_fx():
    return MockBot(nickname="mock_mecha3[BOT]")


@pytest.fixture
def user_fx():
    return User(False,
                None,
                True,
                "unit_test",
                "unit_test[bot]",
                "unit_test",
                "unittest.rats.fuelrats.com",
                "potatobot"
                )


@pytest.fixture
def context_channel_fx(user_fx, bot_fx) -> Context:
    """
    Provides a context fixture

    Returns:
        Context
    """
    context = Context(bot_fx, user_fx, "#unit_test", ["my", "word"], ["my", "my word"])
    return context


@pytest.fixture
def context_pm_fx(user_fx, bot_fx) -> Context:
    """
    Provides a context fixture

    Returns:
        Context
    """
    context = Context(bot_fx, user_fx, "someUSer", ["my", "word"], ["my", "my word"])
    return context


@pytest.fixture(params=[0, 1])
def context_fx(request, bot_fx, user_fx):
    """Parametrized context fixture, returning a channel and non-channel Context object"""
    if request.param == 0:
        return Context(bot_fx, user_fx, "#unit_test", ["my", "word"], ["my", "my word"])
    elif request.param == 1:
        return Context(bot_fx, user_fx, "someUSer", ["my", "word"], ["my", "my word"])

    raise ValueError


@pytest.fixture
def logging_fx(caplog) -> logging.Logger:
    """
    Calls config.setup_logging with a test_log.log file for testing purposes.
    :return:
    """
    caplog.clear()
    return logging.getLogger("mecha.logging_fx")


@pytest.fixture
def spooled_logging_fx(caplog) -> logging.Logger:
    """
    Same as logging_fx, but under separate namespace for the logger to
    use a temporary file.
    """
    caplog.clear()
    return logging.getLogger("mecha.spooled_logging_fx")


@pytest.fixture
def random_string_fx() -> str:
    """
    Creates a 16 digit alphanumeric string.  For use
    with logging tests.

    Returns:
         16 digit alphanumeric string.
    """
    result = "".join(random.sample(string.ascii_letters, 16))
    return result


@pytest.fixture
def epic_fx(rescue_plain_fx, rat_good_fx) -> Epic:
    """Provides an Epic object fixture"""
    return Epic(uuid4(), "my notes package", rescue_plain_fx, rat_good_fx)


@pytest.fixture
def mark_for_deletion_plain_fx() -> MarkForDeletion:
    """Provides a plain MFD object"""
    return MarkForDeletion(False)


@pytest.fixture(params=[(True, 'White Sheets', 'Disallowable cut of jib'),
                        (False, 'Shatt', 'Not Enough Cowbell'),
                        (False, 'unkn0wn', 'Object in mirror appears too close')])
def mark_for_deletion_fx(request) -> MarkForDeletion:
    """Provides a parameterized MFD object"""
    param = request.param
    return MarkForDeletion(marked=param[0], reporter=param[1], reason=param[2])


@pytest.fixture
def rat_cache_fx():
    """provides a empty rat_cache"""
    return RatCache()


@pytest.fixture(autouse=True)
def reset_rat_cache_fx(rat_cache_fx: RatCache):
    """"cleans up the rat_cache's cache"""
    # ensure the cache is clean during setup
    rat_cache_fx.flush()
    yield
    # and clean up after ourselves
    rat_cache_fx.flush()


@pytest.fixture
def permission_fx(monkeypatch) -> Permission:
    """
    Provides a permission fixture

    Args:
        monkeypatch ():

    Returns:

    """
    # ensure _by_vhost is clean prior to running test
    monkeypatch.setattr("Modules.permissions._by_vhost", {})
    permission = Permission(0, {"testing.fuelrats.com", "cheddar.fuelrats.com"})
    return permission


@pytest.fixture
def callable_fx():
    """
    Fixture providing a callable object whose return value can be set and which can be checked for
    having been called.

    See :class:`CallableMock`.
    """
    return CallableMock()


@pytest.fixture
def async_callable_fx():
    """
    Like :func:`callable_fx`, but can be treated as a coroutine function.

    See :class:`AsyncCallableMock`.
    """
    return AsyncCallableMock()


@pytest.fixture(scope="session")
def test_dbm_fx() -> DatabaseManager:
    """
    Test fixture for Database Manager.

    A DATABASE CONFIGURATION AND CONNECTION IS REQUIRED FOR THESE TESTS.
    """
    database = DatabaseManager()
    return database


@pytest.fixture(scope="session")
def test_dbm_pool_fx(test_dbm_fx) -> psycopg2.pool.SimpleConnectionPool:
    """
    Test fixture for Database Manager's connection pool.

    A DATABASE CONFIGURATION AND CONNECTION IS REQUIRED FOR THESE TESTS.
    """
    return test_dbm_fx._dbpool


@pytest.fixture
def test_fact_empty_fx() -> Fact:
    return Fact("", "", [], "", "", "")


@pytest.fixture()
def test_fact_fx() -> Fact:
    return Fact(name='test',
                lang='en',
                message='This is a test fact.',
                aliases=['testfact'],
                author='Shatt',
                editedby='Shatt',
                mfd=False,
                edited=None
                )


@pytest.fixture(params=[WebsocketAPIHandler20, WebsocketAPIHandler21], ids=["v2.0", "v2.1"])
def handler_fx(request):
    """
    Fixture for API handler tests.
    Replaces :fun:`websockets.connect` with a lambda returning the fake object.

    Returns:
        (APIHandler, function, function): A 3-tuple with the following content:
            [0]: A handler instance. Not yet connected.
            [1]: was_sent: A convenience function to test whether or not the aforementioned handler
                sent a given json dict.
            [2]: function: respond: A convenience function to fake a response from the server in the
                mock websocket connection.

    Example:
        >>> async def my_test(handler_fx):
        ...     handler, was_sent, function = handler_fx
        ...     await handler_fx.connect()

    Read below for more information.
    """

    class MockWebsocketConnection(object):
        """Fake websocket connection object to be used with the below convenience functions."""
        def __init__(self):
            super().__init__()
            self.sent_messages = []
            self.incoming_messages = []

            self.host = "some_host"
            self.open = True

        async def recv(self):
            while len(self.incoming_messages) == 0:
                await asyncio.sleep(0.1)

            return json.dumps(self.incoming_messages.pop(0))

        async def close(self, reason):
            self.open = False

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
                        "request_id": next(iter(instance._waiting_requests))
                    }
                }.update(data)
            )

    yield instance, was_sent, respond

    websockets.connect = original_connect
