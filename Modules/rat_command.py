"""
rat_command.py - Handles Command registration and Command-triggering IRC events

Copyright (c) 2018 The Fuel Rat Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md

This module is built on top of the Pydle system.

"""

import logging
import re
from typing import Callable, Dict, Pattern, NamedTuple

from pydle import BasicClient

from Modules.context import Context
from Modules.user import User
from config import config

# set the logger for rat_command
log = logging.getLogger(f"mecha.{__name__}")


class CommandException(Exception):
    """
    base Command Exception
    """
    pass


class InvalidCommandException(CommandException):
    """
    invoked command failed validation
    """
    pass


class CommandNotFoundException(CommandException):
    """
    Command not found.
    """
    pass


class NameCollisionException(CommandException):
    """
    Someone attempted to register a command already registered.
    """
    pass


_registered_commands = {}
_rules: Dict[Pattern, "_RuleTuple"] = {}

# character/s that must prefix a message for it to be parsed as a command.
prefix = config['commands']['prefix']

# Pydle bot instance.
bot: BasicClient = None


async def trigger(message: str, sender: str, channel: str):
    """
    Invoke a command, passing args and kwargs to the called function
    :param message: triggers message to invoke
    :param sender: author of triggering message
    :param channel: channel of triggering message
    :return: bool command
    """
    if bot is None:
        # someone didn't set me.
        raise CommandException(f"Bot client has not been created"
                               f" or not handed to Commands.")

    # check for trigger
    assert message.startswith(prefix), f"message passed that did not contain prefix."

    log.debug(f"Trigger! {message}")

    # remove command prefix
    raw_command: str = message.lstrip(prefix)

    words = []
    words_eol = []
    remaining = raw_command
    while True:
        words_eol.append(remaining)
        try:
            word, remaining = remaining.split(maxsplit=1)
        except ValueError:
            # we couldn't split -> only one word left
            words.append(remaining)
            break
        else:
            words.append(word)

    user = await User.from_whois(bot, sender)
    context = Context(bot, user, channel, words, words_eol)

    if words[0].casefold() in _registered_commands.keys():
        return await _registered_commands[words[0].casefold()](context)
    else:
        for pattern, (coro, full_message, pass_match) in _rules.items():
            if full_message:
                match = pattern.match(words_eol[0])
            else:
                match = pattern.match(words[0])

            if match is not None:
                if pass_match:
                    return await coro(context, match)
                else:
                    return await coro(context)
        else:
            raise CommandNotFoundException(f"Unable to find command {words[0]}")


def _register(func, names: list or str) -> bool:
    """
    Register a new command
    :param func: function
    :param names: names to register
    :return: success
    """
    if isinstance(names, str):
        names = [names]  # idiot proofing

    # transform commands to lowercase
    names = [name.casefold() for name in names]

    if func is None or not callable(func):
        # command not callable
        return False

    else:
        for alias in names:
            if alias in _registered_commands:
                # command already registered
                raise NameCollisionException(f"attempted to re-register command(s) {alias}")
            else:
                formed_dict = {alias: func}
                _registered_commands.update(formed_dict)

        return True


def _flush() -> None:
    """
    Flushes registered commands
    Probably useless outside testing...
    """
    global _registered_commands, _rules  # again this feels ugly but they are module-level now...
    _registered_commands = {}
    _rules = {}


def command(*aliases):
    """
    Registers a command by aliases

    Args:
        *aliases ([str]): aliases to register

    """

    def real_decorator(func: Callable):
        """
        The actual commands decorator

        Args:
            func (Callable): wrapped function

        Returns:
            Callable: *func*, unmodified.
        """
        log.debug(f"Registering command aliases: {aliases}...")
        if not _register(func, aliases):
            raise InvalidCommandException("unable to register commands.")
        log.debug(f"Registration of {aliases} completed.")

        return func
    return real_decorator


_RuleTuple = NamedTuple("_RuleTuple", underlying=Callable, full_message=bool, pass_match=bool)

def rule(regex: str, case_sensitive: bool=False, full_message: bool=False, pass_match: bool=False):
    """
    Decorator to have the underlying coroutine be called when two conditions apply:
    1. No conventional command was found for the incoming message.
    2. The command matches the here provided regular expression.

    Arguments:
        regex (str):
            Regular expression to match the command.
        case_sensitive (bool):
            Whether to match case-sensitively (using the re.IGNORECASE flag).
        full_message (bool):
            If this is True, will try to match against the full message. Otherwise,
            only the word will be matched against.
        pass_match (bool):
            If this is True, the match object will be passed as an argument toward the command
            function.

    Please note that *regex* can match anywhere within the string, it need not match the entire
    string. If you wish to change this behaviour, use '^' and '$' in your regex.
    """
    def decorator(coro: Callable):
        if case_sensitive:
            pattern = re.compile(regex)
        else:
            pattern = re.compile(regex, re.IGNORECASE)

        _rules[pattern] = _RuleTuple(coro, full_message, pass_match)
        log.info(f"New rule matching '{regex}' case-{'' if case_sensitive else 'in'}sensitively was"
                 f" created.")
        return coro
    return decorator
