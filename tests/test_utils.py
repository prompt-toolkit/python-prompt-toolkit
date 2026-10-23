from __future__ import annotations

import itertools

import pytest

from prompt_toolkit.utils import take_using_weights


def test_using_weights():
    def take(generator, count):
        return list(itertools.islice(generator, 0, count))

    # Check distribution.
    data = take(take_using_weights(["A", "B", "C"], [5, 10, 20]), 35)
    assert data.count("A") == 5
    assert data.count("B") == 10
    assert data.count("C") == 20

    assert data == [
        "A",
        "B",
        "C",
        "C",
        "B",
        "C",
        "C",
        "A",
        "B",
        "C",
        "C",
        "B",
        "C",
        "C",
        "A",
        "B",
        "C",
        "C",
        "B",
        "C",
        "C",
        "A",
        "B",
        "C",
        "C",
        "B",
        "C",
        "C",
        "A",
        "B",
        "C",
        "C",
        "B",
        "C",
        "C",
    ]

    # Another order.
    data = take(take_using_weights(["A", "B", "C"], [20, 10, 5]), 35)
    assert data.count("A") == 20
    assert data.count("B") == 10
    assert data.count("C") == 5

    # Bigger numbers.
    data = take(take_using_weights(["A", "B", "C"], [20, 10, 5]), 70)
    assert data.count("A") == 40
    assert data.count("B") == 20
    assert data.count("C") == 10

    # Negative numbers.
    data = take(take_using_weights(["A", "B", "C"], [-20, 10, 0]), 70)
    assert data.count("A") == 0
    assert data.count("B") == 70
    assert data.count("C") == 0

    # All zero-weight items.
    with pytest.raises(ValueError):
        take(take_using_weights(["A", "B", "C"], [0, 0, 0]), 70)


def test_using_weights_yields_one_exact_order():
    """
    The order, and not only the proportions.

    `VSplit` and `HSplit` hand out one cell at a time in this order, so
    two orders with the same proportions still give two layouts: they
    differ by which child gets the last cell.
    """
    for weights, expected in [
        ([1], "AAAAAAAAAAAA"),
        ([7], "AAAAAAAAAAAA"),
        ([1, 1], "ABABABABABABABAB"),
        ([1, 0], "AAAAAAAAAAAA"),
        ([5, 10], "ABBABBABBABBABBABBABBABB"),
        ([1, 1, 1], "ABCABCABCABCABCABCABCABC"),
        ([3, 1, 2], "ABCACAABCACAABCACAABCACA"),
        ([20, 10, 5], "ABCAABAABCAABAABCAABAABCAABAABCAABA"),
        ([1, 2, 3, 4], "ABCDCDBCDDABCDCDBCDDABCDCDBCDD"),
        ([0, 2, 0, 4], "BDDBDDBDDBDDBDDBDDBDDBDD"),
    ]:
        items = list("ABCDEFGH"[: len(weights)])
        taken = itertools.islice(take_using_weights(items, weights), len(expected))

        assert "".join(taken) == expected, weights
