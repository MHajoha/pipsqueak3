import pytest

from Modules.parametrization import parametrize
from Modules import rat_command
from Modules.rat_command import trigger, command
from Modules.context import Context
from tests.mock_callables import AsyncCallableMock


@pytest.fixture(autouse=True)
def setup_fx(bot_fx):
    rat_command.bot = bot_fx
    rat_command._flush()


@pytest.mark.asyncio
async def test_successful_parametrize(async_callable_fx: AsyncCallableMock, bot_fx):
    """Verify that the parametrize decorator passes in the correct arguments."""
    decorated = parametrize("wt", "some_usage")(async_callable_fx)
    decorated = command("wibbly")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test",
                                         "!wibbly wobbly timey wimey")
    await trigger(context)

    assert async_callable_fx.was_called_once
    assert async_callable_fx.was_called_with(context, "wobbly", "timey wimey")


@pytest.mark.asyncio
async def test_parametrize_too_many_args(async_callable_fx: AsyncCallableMock, bot_fx):
    """
    Verify that the parametrize decorator correctly prints out the command usage if too many
    arguments are provided.
    """
    decorated = parametrize("ww", "some_usage")(async_callable_fx)
    decorated = command("wibbly")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test",
                                         "!wibbly wobbly")
    await trigger(context)
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
    decorated = parametrize("ww", "some_usage")(async_callable_fx)
    decorated = command("wibbly")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test",
                                         "!wibbly wobbly timey wimey")
    await trigger(context)
    assert {
               "target": "#channel",
               "message": "usage: !wibbly some_usage"
           } in bot_fx.sent_messages


@pytest.mark.asyncio
async def test_optional_parameter(async_callable_fx: AsyncCallableMock, bot_fx):
    """Test that optional parameters are handled correctly."""
    decorated = parametrize("ww?", "some_usage")(async_callable_fx)
    decorated = command("cmd")(decorated)

    context = await Context.from_message(bot_fx, "#channel", "unit_test", "!cmd arg")
    await trigger(context)

    assert async_callable_fx.was_called_once
    assert async_callable_fx.was_called_with(context, "arg", None)
