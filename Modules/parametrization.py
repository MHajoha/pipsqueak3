from asyncio import iscoroutinefunction
from functools import wraps
from itertools import zip_longest
from typing import Iterable, Callable

from Modules.rat import Rat
from Modules.rat_rescue import Rescue
from config import config
from Modules.context import Context
from Modules.rat_command import log


class _BaseParam(object):
    """Base class for parameters. Do not use directly."""
    _usage_name = None

    def __init__(self, optional: bool=False):
        """
        Initializes a new parameter.

        Args:
            optional:
                Indicates that this argument may be omitted. Mandatory parameters may not follow
                optional ones.
        """
        self.optional = optional

    def __str__(self):
        """Create a user-friendly representation of the parameter for use in usage strings."""
        return f"[{self._usage_name}]" if self.optional else f"<{self._usage_name}>"


class RescueParam(_BaseParam):
    """
    Supplies the command function with an instance of :class:`Rescue`.

    The raw argument can be either the client name, their IRC nickname, the rescue's board index or
    '@' followed by the rescue's UUID.

    This type of parameter has extra options, see :meth:`__init__`.
    """
    _usage_name = "case"

    def __init__(self, *, create: bool=False, include_creation: bool=False, closed: bool=False,
                 optional: bool=False):
        """
        Initializes a new rescue parameter.

        Args:
            create:
                If this is True, a case will be created if none could be found. The raw argument
                will then be interpreted as the client's name. Doesn't work when the raw
                argument is a number or begins with '@'.
            include_creation:
                If this is True, a boolean of whether or not the case was created
                (see *create*) will be added as well.
            closed:
                If this is True, closed cases will be considered as well. Requires an API
                connection.
            optional:
                If this is True, the argument may be omitted. Mandatory parameters may not
                follow optional ones.
        """
        super().__init__(optional)
        self.create = create
        self.include_creation = include_creation


class RatParam(_BaseParam):
    """
    Supplies the command function with an instance of :class:`Rats` found in the rat cache.

    The raw argument can be the rat name, any of their nicknames or '@' followed by the rat's UUID.
    """
    _usage_name = "rat"


class WordParam(_BaseParam):
    """
    Simply forwards the raw argument to the underlying command function.
    """
    _usage_name = "word"


class TextParam(_BaseParam):
    """
    Supplies the command function with the raw argument in question and also everything up to the
    end of the line in a single string argument.
    """
    _usage_name = "text"


def parametrize(*params: _BaseParam, usage: str=None):
    """
    Provides underlying command coroutine with predictable and easy-to-use arguments.

    Arguments:
        *params (_BaseParam):
            Parameters, each of which will be translated into one or more arguments. Available are
            :class:`RescueParam`, :class:`RatParam`, :class:`WordParam` and :class:`TextParam`.
            Check their respective documentation for more info.

            The classes :class:`Rescue` and :class:`Rats` can be used as a shorthand for the default
            configurations of :class:`RescueParam` and :class:`RatParam`.
        usage (str):
            String representing the correct usage of this command. Will be printed if it is used
            incorrectly. If this is omitted, a string will be generated from the parameters.

    Example:
        >>> @parametrize(WordParam(), WordParam(optional=True))
        ... async def some_command(context, rescue1, rescue2_or_none_if_not_provided):
        ...     pass
    """
    def decorator(fun: Callable):
        @wraps(fun)
        async def wrapper(context: Context, *args):
            args: list = [context, *args]

            if len(params) > 0:
                for param, arg, arg_eol in zip_longest(params, context.words[1:],
                                                       context.words_eol[1:]):
                    if param is Rescue or param is RescueParam:
                        param = RescueParam()
                    elif param is Rat or param is RatParam:
                        param = RatParam()
                    elif param is None:
                        if isinstance(params[-1], TextParam):
                            log.debug("Disregarding extra arguments as last parameter was text.")
                            continue
                        else:
                            log.debug(f"Command {context.words[0]} called with too many arguments.")
                            await _reply_usage(context, usage)
                            return

                    if arg is None:
                        # no more arguments provided
                        if param.optional:
                            args.append(None)
                        else:
                            log.debug(f"Mandatory parameter {param} was omitted in "
                                      f"{context.words[0]}.")
                            await _reply_usage(context, usage)
                            return

                    if isinstance(param, RescueParam):
                        # waiting on the rescue board for this
                        raise NotImplementedError("Rescue parameters are not implemented yet")
                    elif isinstance(param, RatParam):
                        raise NotImplementedError("Rat parameters are not implemented yet")
                    elif isinstance(param, WordParam):
                        args.append(arg)
                    elif isinstance(param, TextParam):
                        args.append(arg_eol)
                    else:
                        raise ValueError(f"unrecognized command parameter '{param}'")

            if iscoroutinefunction(fun):
                return await fun(*args)
            else:
                return fun(*args)
        return wrapper
    return decorator


def _generate_usage(params: Iterable[_BaseParam]) -> str:
    result = ""
    for param in params:
        result += param
        result += " "

    return result


def _reply_usage(context: Context, usage: str):
    return context.reply(f"usage: {config['commands']['prefix']}{context.words[0]} {usage}")
