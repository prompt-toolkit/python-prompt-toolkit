from __future__ import annotations

import pytest

from prompt_toolkit.filters import Always, Condition, Filter, Never, to_filter
from prompt_toolkit.filters.base import _AndList, _OrList


def test_never():
    assert not Never()()


def test_always():
    assert Always()()


def test_invert():
    assert not (~Always())()
    assert ~Never()()

    c = ~Condition(lambda: False)
    assert c()


def test_or():
    for a in (True, False):
        for b in (True, False):
            c1 = Condition(lambda: a)
            c2 = Condition(lambda: b)
            c3 = c1 | c2

            assert isinstance(c3, Filter)
            assert c3() == a or b


def test_and():
    for a in (True, False):
        for b in (True, False):
            c1 = Condition(lambda: a)
            c2 = Condition(lambda: b)
            c3 = c1 & c2

            assert isinstance(c3, Filter)
            assert c3() == (a and b)


def test_nested_and():
    for a in (True, False):
        for b in (True, False):
            for c in (True, False):
                c1 = Condition(lambda: a)
                c2 = Condition(lambda: b)
                c3 = Condition(lambda: c)
                c4 = (c1 & c2) & c3

                assert isinstance(c4, Filter)
                assert c4() == (a and b and c)


def test_nested_or():
    for a in (True, False):
        for b in (True, False):
            for c in (True, False):
                c1 = Condition(lambda: a)
                c2 = Condition(lambda: b)
                c3 = Condition(lambda: c)
                c4 = (c1 | c2) | c3

                assert isinstance(c4, Filter)
                assert c4() == (a or b or c)


def test_to_filter():
    f1 = to_filter(True)
    f2 = to_filter(False)
    f3 = to_filter(Condition(lambda: True))
    f4 = to_filter(Condition(lambda: False))

    assert isinstance(f1, Filter)
    assert isinstance(f2, Filter)
    assert isinstance(f3, Filter)
    assert isinstance(f4, Filter)
    assert f1()
    assert not f2()
    assert f3()
    assert not f4()

    with pytest.raises(TypeError):
        to_filter(4)


def test_filter_cache_regression_1():
    # See: https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1729

    cond = Condition(lambda: True)

    # The use of a `WeakValueDictionary` caused this following expression to
    # fail. The problem is that the nested `(a & a)` expression gets garbage
    # collected between the two statements and is removed from our cache.
    x = (cond & cond) & cond
    y = (cond & cond) & cond
    assert x == y


def test_filter_cache_regression_2():
    cond1 = Condition(lambda: True)
    cond2 = Condition(lambda: True)
    cond3 = Condition(lambda: True)

    x = (cond1 & cond2) & cond3
    y = (cond1 & cond2) & cond3
    assert x == y


def test_filter_remove_duplicates():
    cond1 = Condition(lambda: True)
    cond2 = Condition(lambda: True)

    # When a condition is appended to itself using an `&` or `|` operator, it
    # should not be present twice. Having it twice in the `_AndList` or
    # `_OrList` will make them more expensive to evaluate.

    assert isinstance(cond1 & cond1, Condition)
    assert isinstance(cond1 & cond1 & cond1, Condition)
    assert isinstance(cond1 & cond1 & cond2, _AndList)
    assert len((cond1 & cond1 & cond2).filters) == 2

    assert isinstance(cond1 | cond1, Condition)
    assert isinstance(cond1 | cond1 | cond1, Condition)
    assert isinstance(cond1 | cond1 | cond2, _OrList)
    assert len((cond1 | cond1 | cond2).filters) == 2
