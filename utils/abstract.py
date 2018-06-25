from abc import abstractmethod
from typing import Tuple


def abstract(klass: type) -> type:
    """
    Class decorator to prevent a class and all of its subclasses from being instantiated if not all
    abstract members have been overridden.

    Args:
        klass: Class which the decorator is used on.

    Returns:
        type: *klass*, with its `__init_subclass__`  and `__new__` methods replaced.

    The decorated class can not be instantiated. Subclasses of the decorated class can only be
    instantiated if they override all abstract members of their superclasses.

    Examples:
        >>> @abstract
        ... class MyAbstractClass(object):
        ...     @abstractmethod
        ...     def foo(self): ...
        >>> MyAbstractClass()
        Traceback (most recent call last):
            ...
        TypeError: cannot instantiate abstract class

        >>> class MyBadlyDerivedClass(MyAbstractClass):
        ...     pass
        >>> MyBadlyDerivedClass()
        Traceback (most recent call last):
            ...
        TypeError: must override abstract member(s): foo

        >>> class MyWellDerivedClass(MyBadlyDerivedClass):
        ...     def foo(self):
        ...         print("Success!")
        >>> MyWellDerivedClass().foo()
        Success!
    """
    original_new = klass.__new__
    original_init_subclass = klass.__init_subclass__

    def repl_init_subclass(cls, *args, **kwargs):
        original_init_subclass(*args, **kwargs)

        abstracts = _get_abstracts(cls)
        if len(abstracts) > 0:
            def repl_subclass_new(*_, **__):
                raise TypeError(f"must override abstract member(s): {', '.join(abstracts)}")
            cls.__new__ = repl_subclass_new
        else:
            cls.__new__ = original_new
            cls.__init_subclass__ = original_init_subclass

    def repl_new(cls, *args, **kwargs):
        if cls is klass:
            raise TypeError("cannot instantiate abstract class")
        else:
            return original_new(cls, *args, **kwargs)

    klass.__init_subclass__ = classmethod(repl_init_subclass)
    klass.__new__ = repl_new
    return klass


def _get_abstracts(klass: type) -> Tuple[str, ...]:
    # Collect methods
    attrs = {}
    for superclass in reversed(klass.mro()):
        attrs.update(superclass.__dict__)

    # Pick out the names of all abstract attributes
    return tuple(name for name, attr in attrs.items()
                 if getattr(attr, "__isabstractmethod__", False))
