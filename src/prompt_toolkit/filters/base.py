from __future__ import annotations

import weakref
from abc import ABCMeta, abstractmethod
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

__all__ = ["Filter", "Never", "Always", "Condition", "FilterOrBool"]


class Filter(metaclass=ABCMeta):
    """
    Base class for any filter to activate/deactivate a feature, depending on a
    condition.

    The return value of ``__call__`` will tell if the feature should be active.
    """

    def __init__(self) -> None:
        self._and_cache: weakref.WeakValueDictionary[
            Filter, _AndList
        ] = weakref.WeakValueDictionary()
        self._or_cache: weakref.WeakValueDictionary[
            Filter, _OrList
        ] = weakref.WeakValueDictionary()
        self._invert_result: Filter | None = None

    @abstractmethod
    def __call__(self) -> bool:
        """
        The actual call to evaluate the filter.
        """
        return True

    def __and__(self, other: Filter) -> Filter:
        """
        Chaining of filters using the & operator.
        """
        assert isinstance(other, Filter), "Expecting filter, got %r" % other

        if isinstance(other, Always):
            return self
        if isinstance(other, Never):
            return other

        if other in self._and_cache:
            return self._and_cache[other]

        result = _AndList([self, other])
        self._and_cache[other] = result
        return result

    def __or__(self, other: Filter) -> Filter:
        """
        Chaining of filters using the | operator.
        """
        assert isinstance(other, Filter), "Expecting filter, got %r" % other

        if isinstance(other, Always):
            return other
        if isinstance(other, Never):
            return self

        if other in self._or_cache:
            return self._or_cache[other]

        result = _OrList([self, other])
        self._or_cache[other] = result
        return result

    def __invert__(self) -> Filter:
        """
        Inverting of filters using the ~ operator.
        """
        if self._invert_result is None:
            self._invert_result = _Invert(self)

        return self._invert_result

    def __bool__(self) -> None:
        """
        By purpose, we don't allow bool(...) operations directly on a filter,
        because the meaning is ambiguous.

        Executing a filter has to be done always by calling it. Providing
        defaults for `None` values should be done through an `is None` check
        instead of for instance ``filter1 or Always()``.
        """
        raise ValueError(
            "The truth value of a Filter is ambiguous. "
            "Instead, call it as a function."
        )


class _AndList(Filter):
    """
    Result of &-operation between several filters.
    """

    def __init__(self, filters: Iterable[Filter]) -> None:
        super().__init__()
        self.filters: list[Filter] = []

        for f in filters:
            if isinstance(f, _AndList):  # Turn nested _AndLists into one.
                self.filters.extend(f.filters)
            else:
                self.filters.append(f)

    def __call__(self) -> bool:
        return all(f() for f in self.filters)

    def __repr__(self) -> str:
        return "&".join(repr(f) for f in self.filters)


class _OrList(Filter):
    """
    Result of |-operation between several filters.
    """

    def __init__(self, filters: Iterable[Filter]) -> None:
        super().__init__()
        self.filters: list[Filter] = []

        for f in filters:
            if isinstance(f, _OrList):  # Turn nested _OrLists into one.
                self.filters.extend(f.filters)
            else:
                self.filters.append(f)

    def __call__(self) -> bool:
        return any(f() for f in self.filters)

    def __repr__(self) -> str:
        return "|".join(repr(f) for f in self.filters)


class _Invert(Filter):
    """
    Negation of another filter.
    """

    def __init__(self, filter: Filter) -> None:
        super().__init__()
        self.filter = filter

    def __call__(self) -> bool:
        return not self.filter()

    def __repr__(self) -> str:
        return "~%r" % self.filter


class Always(Filter):
    """
    Always enable feature.
    """

    def __call__(self) -> bool:
        return True

    def __or__(self, other: Filter) -> Filter:
        return self

    def __invert__(self) -> Never:
        return Never()


class Never(Filter):
    """
    Never enable feature.
    """

    def __call__(self) -> bool:
        return False

    def __and__(self, other: Filter) -> Filter:
        return self

    def __invert__(self) -> Always:
        return Always()


class Condition(Filter):
    """
    Turn any callable into a Filter. The callable is supposed to not take any
    arguments.

    This can be used as a decorator::

        @Condition
        def feature_is_active():  # `feature_is_active` becomes a Filter.
            return True

    :param func: Callable which takes no inputs and returns a boolean.
    """

    def __init__(self, func: Callable[[], bool]) -> None:
        super().__init__()
        self.func = func

    def __call__(self) -> bool:
        return self.func()

    def __repr__(self) -> str:
        return "Condition(%r)" % self.func


# Often used as type annotation.
FilterOrBool = Union[Filter, bool]
