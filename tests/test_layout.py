from __future__ import annotations

import pytest

from prompt_toolkit import Application
from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.layout import InvalidLayoutError, Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets import TextArea


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


@pytest.mark.parametrize("height", [1, 2])
@pytest.mark.parametrize(
    "prompt,prefix,character",
    [
        ("", "", " "),
        (">>> ", "", " "),
        ("界> ", "", " "),
        ("", ".. ", " "),
        (">>> ", ".. ", " "),
        (">>> ", "界 ", " "),
        (">>> ", "", "界"),
        (">>> ", ".. ", "界"),
    ],
)
def test_wrapped_text_area_cursor(height, prompt, prefix, character):
    class Output(DummyOutput):
        def get_size(self):
            return Size(rows=height, columns=20)

    prefix_width = get_cwidth(prefix)
    text = "x" * (20 - get_cwidth(prompt) - prefix_width - 1)
    text += "x" * ((height - 1) * (20 - prefix_width))
    area = TextArea(
        multiline=height > 1,
        height=height,
        wrap_lines=True,
        prompt=prompt,
        get_line_prefix=(lambda lineno, wrap_count: prefix) if prefix else None,
    )
    # Fill the window, type at the wrap boundary, then move back and insert.
    keys = iter([text, "x", character, "\x1b[D", "X"])
    positions = []
    last_document = None

    with create_pipe_input() as inp:

        def after_render(app):
            nonlocal last_document
            if app.is_done or area.document == last_document:
                return
            last_document = area.document
            info = area.window.render_info
            positions.append((info.cursor_position, area.window.vertical_scroll_2))
            key = next(keys, None)
            if key is None:
                app.exit()
            else:
                inp.send_text(key)

        app = Application(
            layout=Layout(area),
            input=inp,
            output=Output(),
            full_screen=True,
            after_render=after_render,
        )
        app.run()

    assert positions[1:] == [
        (Point(x=19, y=height - 1), 0),
        (Point(x=prefix_width, y=height - 1), 1),
        (Point(x=prefix_width + get_cwidth(character), y=height - 1), 1),
        (Point(x=prefix_width, y=height - 1), 1),
        (Point(x=prefix_width + 1, y=height - 1), 1),
    ]
    assert area.text == text + "xX" + character
    assert area.buffer.cursor_position == len(text) + 2
