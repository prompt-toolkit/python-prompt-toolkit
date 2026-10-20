from __future__ import annotations

import pytest

from prompt_toolkit.layout import InvalidLayoutError, Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.utils import explode_text_fragments


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


@pytest.mark.parametrize("index", [-3, -2, -1, 0, 1, 2])
@pytest.mark.parametrize("text", ["", "X", "YZ"])
def test_exploded_list_assign_item(index, text):
    fragments = explode_text_fragments([("", "abc")])
    fragments[index] = ("bold", text)

    normalized_index = index % 3
    expected = [("", char) for char in "abc"]
    expected[normalized_index : normalized_index + 1] = [
        ("bold", char) for char in text
    ]
    assert fragments == expected


@pytest.mark.parametrize("text, index", [("abc", -4), ("abc", 3), ("", -1), ("", 0)])
def test_exploded_list_assign_item_out_of_range(text, index):
    fragments = explode_text_fragments([("", text)])
    original = fragments[:]

    with pytest.raises(IndexError):
        fragments[index] = ("bold", "X")
    assert fragments == original


def test_exploded_list_assign_index_object():
    class LastIndex:
        def __index__(self):
            return -1

    fragments = explode_text_fragments([("", "abc")])
    fragments[LastIndex()] = ("bold", "XY")
    assert fragments == [("", "a"), ("", "b"), ("bold", "X"), ("bold", "Y")]
