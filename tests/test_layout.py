from __future__ import annotations

import pytest

from prompt_toolkit.layout import InvalidLayoutError, Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.dimension import Dimension, max_layout_dimensions


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


@pytest.mark.parametrize(
    "dimensions, expected",
    [
        ([Dimension(max=10)], (0, 10, 0)),
        ([Dimension(max=10, preferred=0)], (0, 10, 0)),
        ([Dimension.zero(), Dimension(max=10)], (0, 10, 0)),
        ([Dimension(), Dimension(max=10)], (0, 10, 0)),
        ([Dimension(max=10), Dimension(max=20)], (0, 10, 0)),
        ([Dimension(max=10), Dimension(max=20, preferred=5)], (0, 10, 5)),
        ([Dimension(max=10), Dimension(max=20, preferred=12)], (0, 12, 12)),
        ([], (0, 0, 0)),
        ([Dimension.zero()], (0, 0, 0)),
        ([Dimension.zero(), Dimension.exact(8)], (8, 8, 8)),
    ],
)
def test_max_layout_dimensions_preserves_zero_preferred_max(dimensions, expected):
    dimension = max_layout_dimensions(dimensions)
    assert (dimension.min, dimension.max, dimension.preferred) == expected


def test_nested_split_preserves_zero_preferred_width_limit():
    child = HSplit([Window(width=Dimension(max=10, preferred=0))])

    assert child.preferred_width(80).max == 10
    assert VSplit([child, Window()])._divide_widths(80) == [10, 0, 70]
