from functools import wraps
from itertools import zip_longest
from typing import List

from config import config
from Modules.context import Context
from Modules.rat_command import log


def parametrize(params: str, usage: str):
    """
    Provides underlying command coroutine with predictable and easy-to-use arguments.

    Arguments:
        params: String of parameters which will each be translated into an argument.

            * 'c': Argument will be the `Rescue` object found on the local board.
            * 'C': Same as 'c', but creates the case if it doesn't exist.
            * 'F': Same as 'C', but generating an additional boolean argument of whether or not
              the case was created.
            * 'r': Argument will be the `Rats` object found.
            * 'w': Argument will be a single word (separated by whitespace).
            * 't': Argument will be everything from here up to the end of the line.

            * '?': Marks the previous parameter as optional. If it isn't provided, don't complain.
              Optional parameters may not precede mandatory ones. Argument will be None if not provided.
        usage (str): String representing the correct usage of this command. Will be printed if
            it is used wrongly.

    Example:
        >>> @parametrize("cc?", "<first case> <optional second case>")
        ... async def some_command(context, rescue1, rescue2_or_none_if_not_provided):
        ...     pass
    """
    params = _prettify_params(params)

    def decorator(coro):
        @wraps(coro)
        async def new_coro(context: Context):
            args = [context]

            for param, arg, arg_eol in zip_longest(params, context.words[1:],
                                                   context.words_eol[1:]):
                if param is None:
                    if params[-1] == "t":
                        log.debug("Disregarding extra arguments as last parameter was text.")
                    else:
                        log.debug(f"Command {context.words[0]} called with too many arguments.")
                        return await context.reply(f"usage: {config['commands']['prefix']}"
                                                   f"{context.words[0]} {usage}")
                elif arg is None:
                    # no more arguments provided
                    if param.optional:
                        args.append(None)
                    else:
                        log.debug(f"Mandatory parameter {param} was omitted in "
                                  f"{context.words[0]}.")
                        return await context.reply(f"usage: {config['commands']['prefix']}"
                                                   f"{context.words[0]} {usage}")

                elif param.matches("cf"):
                    # waiting on the rescue board for this
                    raise NotImplementedError("Rescue parameters are not implemented yet")
                elif param == "r":
                    raise NotImplementedError("Rat parameters are not implemented yet")
                elif param == "w":
                    args.append(arg)
                elif param == "t":
                    args.append(arg_eol)
                else:
                    raise ValueError(f"unrecognized command parameter '{param}'")

            return await coro(*args)
        return new_coro
    return decorator


class _Param(object):
    """Helper object used by `Commands.parametrize`"""
    def __init__(self, param_char: str, optional: bool=False, create: bool=False):
        self.char = param_char
        self.optional = optional
        self.create = create

    def __eq__(self, other):
        if self is other:
            return True
        elif isinstance(other, _Param):
            return self.char.lower() == other.char.lower() and \
                   self.optional == other.optional and \
                   self.create == other.create
        elif isinstance(other, str):
            return self.char.lower() == other.lower()
        else:
            return False

    def __str__(self):
        return "{}{}".format(
            self.char.upper() if self.create else self.char.lower(),
            '?' if self.optional else ""
        )

    def matches(self, params: str):
        """
        Example:
            >>> _Param("b").matches("abc")
            True
            >>> _Param("c").matches("ab")
            False
        """
        return self.char.lower() in params.lower()


def _prettify_params(params: str) -> List[_Param]:
    """
    Helper method for `parametrize`.

    Arguments:
        params (str): Raw parameter string as passed to the decorator.

    Returns:
        [_Param]: Representation of parameters as a list of easy-to-use `_Param` objects.
    """
    pretty_params = []
    for param in params:
        if param == "?":
            if len(pretty_params) >= 1:
                pretty_params[-1].optional = True
            else:
                raise ValueError(f"got '?' modifier before parameter in {params}")
        else:
            pretty_params.append(_Param(param))

        if param.isupper():
            pretty_params[-1].create = True

    return pretty_params
