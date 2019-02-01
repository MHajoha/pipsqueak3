from abc import ABC, abstractproperty, abstractmethod
from asyncio import iscoroutine
from enum import Enum, auto
from functools import wraps
from typing import Iterable, Callable, Iterator, Tuple, Any, List
from uuid import UUID

from Modules.rat import Rat
from Modules.rat_cache import RatCache
from Modules.rat_rescue import Rescue
from config import config
from Modules.context import Context
from Modules.rat_command import log


class _EvaluationResult(Enum):
    CONTINUE = auto()
    DONE = auto()
    CANCEL = auto()


class _ArgumentProvider(Iterator[Tuple[str, str]]):
    def __init__(self, context: Context):
        self._context = context
        self._index = 1
        self._is_at_end = False

    @property
    def context(self) -> Context:
        return self._context

    @property
    def is_at_end(self) -> bool:
        return self._is_at_end

    def next_arg(self) -> str:
        if self.is_at_end:
            raise ValueError("no arguments are left")
        else:
            result = self.context.words[self._index]
            self._index += 1
            if self._index >= len(self.context.words):
                self._is_at_end = True
            return result

    def next_arg_eol(self) -> str:
        if self.is_at_end:
            raise ValueError("no arguments are left")
        else:
            self._is_at_end = True
            return self.context.words_eol[self._index]

    def __next__(self) -> str:
        if self.is_at_end:
            raise StopIteration
        else:
            return self.next_arg()


class _AbstractParam(ABC):
    """Abstract base class for parameters."""
    _usage_name = abstractproperty()

    def __init__(self, optional: bool = False):
        """
        Initializes a new parameter.

        Args:
            optional:
                Indicates that this argument may be omitted. Mandatory parameters may not follow
                optional ones.
        """
        self.optional = optional

    @abstractmethod
    async def evaluate(self, state: _ArgumentProvider, target_args: List[Any]) -> _EvaluationResult: ...

    def __str__(self):
        """Create a user-friendly representation of the parameter for use in usage strings."""
        return f"[{self._usage_name}]" if self.optional else f"<{self._usage_name}>"

    def __repr__(self):
        """Create a developer-friendly representation of the parameter."""
        return type(self).__name__ + ("(optional)" if self.optional else "()")


class RescueParam(_AbstractParam):
    """
    Supplies the command function with an instance of :class:`Rescue`.

    The raw argument can be either the client name, their IRC nickname, the rescue's board index or
    '@' followed by the rescue's UUID.

    This type of parameter has extra options, see :meth:`__init__`.
    """
    _usage_name = "case"

    def __init__(self, *, create: bool = False, include_creation: bool = False,
                 closed: bool = False,
                 optional: bool = False):
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
        self.closed = closed

    def __repr__(self):
        result = type(self).__name__ + "("
        for flag, name in ((self.create, "create"), (self.include_creation, "include_creation"),
                           (self.closed, "closed"), (self.optional, "optional")):
            if flag:
                result += name + ", "

        return result


class RatParam(_AbstractParam):
    """
    Supplies the command function with an instance of :class:`Rats` found in the rat cache.

    The raw argument can be the rat name, any of their nicknames or '@' followed by the rat's UUID.
    """
    _usage_name = "rat"

    async def evaluate(self, state: _ArgumentProvider, target_args: List[Any]) -> _EvaluationResult:
        arg = state.next_arg()
        if arg.startswith("@"):
            try:
                uuid = UUID(arg[1:])
            except ValueError:
                log.warn(f"Argument for rat starts with @, but was not a valid "
                         f"UUID: {arg}")
            except IndexError:
                log.warn(f"Argument for rat is a sole @")
            else:
                found_rat = await RatCache().get_rat_by_uuid(uuid)
                if found_rat is None:
                    log.info(f"Could not find a rat with UUID {uuid}")
                    await state.context.reply(
                        f"{state.context.user.nickname}: Could not find rat with ID {uuid}!")
                    return _EvaluationResult.CANCEL
                else:
                    target_args.append(found_rat)
                    return _EvaluationResult.CONTINUE

        found_rat = await RatCache().get_rat_by_name(arg)
        if found_rat is None:
            log.info(f"Could not find a rat with name {arg}")
            await state.context.reply(
                f"{state.context.user.nickname}: Could not find rat '{arg}'!")
            return _EvaluationResult.CANCEL
        else:
            target_args.append(found_rat)
            return _EvaluationResult.CONTINUE


class WordParam(_AbstractParam):
    """
    Simply forwards the raw argument to the underlying command function.
    """
    _usage_name = "word"

    async def evaluate(self, state: _ArgumentProvider, target_args: List[Any]):
        target_args.append(state.next_arg())
        return _EvaluationResult.CONTINUE


class TextParam(_AbstractParam):
    """
    Supplies the command function with the raw argument in question and also everything up to the
    end of the line in a single string argument.
    This Parameter is terminal. No other parameters must follow it.
    """
    _usage_name = "text"

    async def evaluate(self, state: _ArgumentProvider, target_args: List[Any]):
        target_args.append(state.next_arg_eol())
        return _EvaluationResult.DONE


def parametrize(*params: _AbstractParam, usage: str = None):
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
            state = _ArgumentProvider(context)
            target_args = [context, *args]

            for param in params:
                if param is Rescue or param is RescueParam:
                    param = RescueParam()
                elif param is Rat or param is RatParam:
                    param = RatParam()

                if state.is_at_end:
                    # no more arguments provided
                    if param.optional:
                        target_args.append(None)
                        continue
                    else:
                        log.debug(f"Mandatory parameter {repr(param)} was omitted in "
                                  f"{context.words[0]}.")
                        await _reply_usage(context, usage)
                        return

                evaluation_result = await param.evaluate(state, target_args)
                if evaluation_result is _EvaluationResult.CONTINUE:
                    continue
                elif evaluation_result is _EvaluationResult.DONE:
                    break
                else:
                    return

            if not state.is_at_end:
                log.debug(f"Command {context.words[0]} called with too many arguments.")
                await _reply_usage(context, usage)
                return

            result = fun(*target_args)
            if iscoroutine(result):
                return await result
            else:
                return result

        return wrapper

    return decorator


def _generate_usage(params: Iterable[_AbstractParam]) -> str:
    result = ""
    for param in params:
        result += param
        result += " "

    return result


def _reply_usage(context: Context, usage: str):
    return context.reply(f"usage: {config['commands']['prefix']}{context.words[0]} {usage}")
