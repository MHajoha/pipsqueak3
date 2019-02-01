from typing import Tuple
from uuid import UUID

import pytest

from Modules.parametrization import parametrize, TextParam, WordParam, _AbstractParam, RatParam
from Modules import rat_command
from Modules.rat import Rat
from Modules.rat_command import trigger, command
from Modules.context import Context
from tests.mock_callables import AsyncCallableMock


@pytest.fixture(autouse=True)
def setup_fx(bot_fx):
    rat_command.bot = bot_fx
    rat_command._flush()


@pytest.fixture
def rat_fx(rat_good_fx, rat_cache_fx):
    rat_cache_fx.flush()
    rat_cache_fx.by_uuid[rat_good_fx.uuid] = rat_good_fx
    rat_cache_fx.by_name[rat_good_fx.name] = rat_good_fx
    return rat_good_fx


@pytest.mark.parametrize("params,trigger_string,expected_arguments",
                         [((WordParam(), TextParam()),
                           "!test wibbly wobbly timey wimey",
                           ("wibbly", "wobbly timey wimey")),
                          ((WordParam(), WordParam(), WordParam(optional=True)),
                           "!test no more",
                           ("no", "more", None))])
@pytest.mark.asyncio
async def test_simple_parametrize(params: Tuple[_AbstractParam, ...], trigger_string: str,
                                  expected_arguments: tuple,
                                  async_callable_fx: AsyncCallableMock, bot_fx):
    """Verify that the parametrize decorator passes in the correct arguments."""
    decorated = parametrize(*params)(async_callable_fx)
    decorated = command("test")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test",
                                         trigger_string)
    await trigger(context)

    assert async_callable_fx.was_called_once
    assert async_callable_fx.was_called_with(context, *expected_arguments)


@pytest.mark.asyncio
async def test_parametrize_too_many_args(async_callable_fx: AsyncCallableMock, bot_fx):
    """
    Verify that the parametrize decorator correctly prints out the command usage if too many
    arguments are provided.
    """
    decorated = parametrize(WordParam(), usage="some_usage")(async_callable_fx)
    decorated = command("wibbly")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test",
                                         "!wibbly wobbly timey wimey")
    await trigger(context)
    assert not async_callable_fx.was_called
    assert {
               "target": "#channel",
               "message": "usage: !wibbly some_usage"
           } in bot_fx.sent_messages


@pytest.mark.asyncio
async def test_parametrize_too_few_args(async_callable_fx: AsyncCallableMock, bot_fx):
    """
    Verify that the parametrize decorator correctly prints out the command usage if mandatory
    parameters are omitted.
    """
    decorated = parametrize(WordParam(), WordParam(), usage="some_usage")(async_callable_fx)
    decorated = command("wibbly")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test",
                                         "!wibbly wobbly")
    await trigger(context)
    assert not async_callable_fx.was_called
    assert {
               "target": "#channel",
               "message": "usage: !wibbly some_usage"
           } in bot_fx.sent_messages


@pytest.mark.asyncio
async def test_optional_parameter(async_callable_fx: AsyncCallableMock, bot_fx):
    """Test that optional parameters are handled correctly."""
    decorated = parametrize(WordParam(), WordParam(optional=True))(async_callable_fx)
    decorated = command("cmd")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test", "!cmd arg")
    await trigger(context)

    assert async_callable_fx.was_called_once
    assert async_callable_fx.was_called_with(context, "arg", None)


@pytest.mark.asyncio
async def test_rat_parameter_by_name(rat_fx: Rat, async_callable_fx: AsyncCallableMock,
                                     bot_fx):
    """Verify that the parametrize decorator passes in the rat correct when the name is given."""
    decorated = parametrize(RatParam())(async_callable_fx)
    decorated = command("test")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test",
                                         f"!test {rat_fx.name}")
    await trigger(context)

    assert async_callable_fx.was_called_once
    assert async_callable_fx.was_called_with(context, rat_fx)


@pytest.mark.asyncio
async def test_rat_parameter_not_found_by_name(rat_fx: Rat, async_callable_fx: AsyncCallableMock,
                                               bot_fx):
    """
    Verify that the correct reply is sent and the command function isn't called when the rat
    with the given name can't be found.
    """
    decorated = parametrize(RatParam())(async_callable_fx)
    decorated = command("test")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test",
                                         f"!test theRatName{rat_fx.name}butMore")
    await trigger(context)

    assert not async_callable_fx.was_called_once
    assert {
               "target": "#channel",
               "message": f"unit_test: Could not find rat 'theRatName{rat_fx.name}butMore'!"
           } in bot_fx.sent_messages


@pytest.mark.asyncio
async def test_rat_parameter_by_uuid(rat_fx: Rat, async_callable_fx: AsyncCallableMock,
                                     bot_fx):
    """Verify that the parametrize decorator passes in the rat correct when the ID is given."""
    decorated = parametrize(RatParam())(async_callable_fx)
    decorated = command("test")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test",
                                         f"!test @{rat_fx.uuid}")
    await trigger(context)

    assert async_callable_fx.was_called_once
    assert async_callable_fx.was_called_with(context, rat_fx)


@pytest.mark.asyncio
async def test_rat_parameter_not_found_by_uuid(rat_fx: Rat, async_callable_fx: AsyncCallableMock,
                                               bot_fx):
    """
    Verify that the correct reply is sent and the command function isn't called when the rat
    with the given ID can't be found.
    """
    decorated = parametrize(RatParam())(async_callable_fx)
    decorated = command("test")(decorated)

    wrong_uuid = UUID(int=rat_fx.uuid.int + 1)
    context = await Context.from_message(bot_fx, "#channel", "unit_test",
                                         f"!test @{wrong_uuid}")
    await trigger(context)

    assert not async_callable_fx.was_called_once
    assert {
               "target": "#channel",
               "message": f"unit_test: Could not find rat with ID {wrong_uuid}!"
           } in bot_fx.sent_messages
