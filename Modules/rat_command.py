"""
rat_command.py - Handles Command registration and Command-triggering IRC events

Copyright (c) 2018 The Fuel Rat Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md

This module is built on top of the Pydle system.

"""

import logging
from functools import wraps
from typing import Callable, Any, List
from itertools import zip_longest
from enum import Enum

from pydle import BasicClient

from Modules.context import Context
from Modules.rules import get_rule, clear_rules
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


class NameCollisionException(CommandException):
    """
    Someone attempted to register a command already registered.
    """
    pass


_registered_commands = {}

# character/s that must prefix a message for it to be parsed as a command.
prefix = config['commands']['prefix']


async def trigger(ctx) -> Any:
    """

    Args:
        ctx (Context): Invocation context

    Returns:
        result of command execution
    """

    if ctx.words_eol[0] == "":
        return  # empty message, bail out

    if ctx.prefixed:
        if ctx.words[0].casefold() in _registered_commands:
            # A regular command
            command_fun = _registered_commands[ctx.words[0].casefold()]
            extra_args = ()
            log.debug(f"Regular command {ctx.words[0]} invoked.")
        else:
            # Might be a regular rule
            command_fun, extra_args = get_rule(ctx.words, ctx.words_eol, prefixless=False)
            if command_fun:
                log.debug(
                    f"Rule {getattr(command_fun, '__name__', '')} matching {ctx.words[0]} found.")
            else:
                log.debug(f"Could not find command or rule for {prefix}{ctx.words[0]}.")
    else:
        # Might still be a prefixless rule
        command_fun, extra_args = get_rule(ctx.words, ctx.words_eol, prefixless=True)
        if command_fun:
            log.debug(
                f"Prefixless rule {getattr(command_fun, '__name__', '')} matching {ctx.words[0]} "
                f"found.")

    if command_fun:
        return await command_fun(ctx, *extra_args)
    else:
        log.debug(f"Ignoring message '{ctx.words_eol[0]}'. Not a command or rule.")


class _Param(Enum):
    """Helper object used by `Commands.parametrize`"""
    def __init__(self, *args, **kwargs):
        self.optional = False
        self.create = False

    CASE = 0
    FIND = 1
    RAT = 2
    WORD = 3
    TEXT = 4


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
    global _registered_commands  # again this feels ugly but they are module-level now...
    _registered_commands = {}
    clear_rules()


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


def parametrize(params: str, usage: str):
    """
    Provides underlying command coroutine with predictable and easy-to-use arguments.

    Arguments:
        params: String of parameters which will each be translated into an argument. Some of these are TODO.
            'c': Argument will be the `Rescue` object returned by `RescueBoard.find`.
            'C': Same as 'c', but creates the case if it doesn't exist.
            'f': Same as 'c', but returning `(Rescue, bool)` as returned by `RescueBoard.find`.
            'F': Same as 'C', but returning `(Rescue, bool)` as returned by `RescueBoard.find`.
            'r': Argument will be the `Rat` object found.
            'w': Argument will be a single word (separated by whitespace).
            't': Argument will be everything from here up to the end of the line.

            '?': Marks the previous parameter as optional. If it isn't provided, don't complain. Optional parameters
                may not precede mandatory ones. Argument will be None if not provided.
        usage (str): String representing the correct usage of this command. Will be printed if it is used wrongly.

    Example:
        ``
        @parametrize("cc?")
        async def some_command(context, rescue1, rescue2_or_none_if_not_provided): pass
        ``
    """
    params = _prettify_params(params)

    def decorator(coro):
        @wraps(coro)
        async def new_coro(context: Context):
            args = [context]

            for param, arg, arg_eol in zip_longest(params,
                                                   context.words[1:], context.words_eol[1:]):
                if param is None:
                    # too many arguments provided
                    return context.reply(
                        f"usage: {config['commands']['prefix']}{context.words[0]} {usage}")
                elif arg is None:
                    # no more arguments provided
                    if param.optional:
                        args.append(None)
                    else:
                        return context.reply(
                            f"usage: {config['commands']['prefix']}{context.words[0]} {usage}")

                elif param in (_Param.CASE, _Param.FIND):
                    # waiting on the rescue board for this
                    raise NotImplementedError("Rescue parameters are not implemented yet")
                elif param == _Param.RAT:
                    raise NotImplementedError("Rat parameters are not implemented yet")
                elif param == _Param.WORD:
                    args.append(arg)
                elif param == _Param.TEXT:
                    args.append(arg_eol)

            return await coro(*args)

        return new_coro

    return decorator


def _prettify_params(params: str) -> List[_Param]:
    """Helper method for `parametrize`"""
    pretty_params = []
    for i, param in enumerate(params):
        if param in "cC":
            pretty_params.append(_Param.CASE)
        elif param in "fF":
            pretty_params.append(_Param.FIND)
        elif param == "r":
            pretty_params.append(_Param.RAT)
        elif param == "w":
            pretty_params.append(_Param.WORD)
        elif param == "t":
            pretty_params.append(_Param.TEXT)
        elif param == "?":
            continue  # was handled in the previous iteration
        else:
            raise ValueError("unrecognized command parameter: {}".format(param))

        if param in "CF":
            pretty_params[-1].create = True
        if i < len(params) - 1 and params[i + 1] == "?":
            pretty_params[-1].optional = True

    return pretty_params
