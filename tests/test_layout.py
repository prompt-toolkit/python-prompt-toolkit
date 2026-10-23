from __future__ import annotations

from random import Random

import pytest

from prompt_toolkit.layout import InvalidLayoutError, Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.dimension import Dimension


def test_layout_class():
    c1 = BufferControl()
    c2 = BufferControl()
    c3 = BufferControl()
    win1 = Window(content=c1)
    win2 = Window(content=c2)
    win3 = Window(content=c3)

    layout = Layout(container=VSplit([HSplit([win1, win2]), win3]))

    # Listing of windows/controls.
    assert list(layout.find_all_windows()) == [win1, win2, win3]
    assert list(layout.find_all_controls()) == [c1, c2, c3]

    # Focusing something.
    layout.focus(c1)
    assert layout.has_focus(c1)
    assert layout.has_focus(win1)
    assert layout.current_control == c1
    assert layout.previous_control == c1

    layout.focus(c2)
    assert layout.has_focus(c2)
    assert layout.has_focus(win2)
    assert layout.current_control == c2
    assert layout.previous_control == c1

    layout.focus(win3)
    assert layout.has_focus(c3)
    assert layout.has_focus(win3)
    assert layout.current_control == c3
    assert layout.previous_control == c2

    # Pop focus. This should focus the previous control again.
    layout.focus_last()
    assert layout.has_focus(c2)
    assert layout.has_focus(win2)
    assert layout.current_control == c2
    assert layout.previous_control == c1


def test_create_invalid_layout():
    with pytest.raises(InvalidLayoutError):
        Layout(HSplit([]))


def test_divide_widths_hands_out_exactly_what_fits():
    """
    `_divide_widths` grows each child one unit at a time and carries the
    handed-out total in a local rather than re-adding it. Whatever the
    loop does, the answer keeps three promises: too little room gives
    back nothing, every child stays inside its own minimum and maximum,
    and the sizes add up to everything the split may take. A local that
    drifted from the true total in either direction would break the
    third promise, so this pins the carried total as well as the loop.
    """
    rng = Random(0)

    for _ in range(200):
        children = []
        for _ in range(rng.randint(1, 4)):
            minimum = rng.randint(0, 5)
            preferred = minimum + rng.randint(0, 10)
            children.append(
                Window(
                    width=Dimension(
                        min=minimum,
                        preferred=preferred,
                        max=preferred + rng.randint(0, 10),
                        weight=rng.randint(1, 3),
                    )
                )
            )

        width = rng.randint(0, 30)
        split = VSplit(children)
        actual = [c.preferred_width(width) for c in split._all_children]
        sizes = split._divide_widths(width)

        if sum(d.min for d in actual) > width:
            assert sizes is None
            continue

        assert sizes is not None
        assert len(sizes) == len(actual)
        assert all(d.min <= s <= d.max for s, d in zip(sizes, actual))
        assert sum(sizes) == min(width, sum(d.max for d in actual))
