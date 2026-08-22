from __future__ import annotations

from contextlib import contextmanager

import pytest

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import set_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.data_structures import Point
from prompt_toolkit.document import Document
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.layout import InvalidLayoutError, Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.layout.screen import Screen, WritePosition
from prompt_toolkit.output import DummyOutput


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


@contextmanager
def _render_wrapped_buffer(text, *, width, height, prompt="", cursor_position=None):
    """Render a single-line wrapped BufferControl and yield (window, screen)."""
    if cursor_position is None:
        cursor_position = len(text)
    buf = Buffer(document=Document(text, cursor_position), multiline=False)
    buf._load_history_task = True  # Skip async history loading in tests.
    processors = [BeforeInput(prompt)] if prompt else None
    control = BufferControl(
        buffer=buf,
        input_processors=processors,
        include_default_input_processors=False,
    )
    win = Window(content=control, wrap_lines=True)
    with create_pipe_input() as inp:
        app = Application(layout=Layout(win), output=DummyOutput(), input=inp)
        with set_app(app):
            screen = Screen()
            win.write_to_screen(
                screen,
                MouseHandlers(),
                WritePosition(0, 0, width, height),
                "",
                False,
                None,
            )
            yield win, screen, control


def test_get_height_for_line_cursor_at_wrap_boundary():
    """Cursor after a full visual line sits on the next wrapped row (issue #2071)."""
    text = "1234567890"  # Exact multiple of width; extra cursor cell wraps.
    with _render_wrapped_buffer(text, width=10, height=4) as (win, screen, control):
        content = control.create_content(10, 4)
        # Full line includes the trailing cursor space, so it needs 2 rows.
        assert content.get_height_for_line(0, 10, None) == 2
        # Text before the cursor fills the width exactly; cursor is on row 2.
        assert (
            content.get_height_for_line(
                0, 10, None, slice_stop=content.cursor_position.x
            )
            == 2
        )
        assert screen.get_cursor_position(win) == Point(x=0, y=1)


def test_get_height_for_line_exact_width_without_cursor_slice():
    """A line that exactly fills the width (including cursor cell) is one row."""
    # 9 chars + trailing cursor space = width 10.
    text = "123456789"
    with _render_wrapped_buffer(text, width=10, height=2) as (win, screen, control):
        content = control.create_content(10, 2)
        assert content.get_height_for_line(0, 10, None) == 1
        assert (
            content.get_height_for_line(
                0, 10, None, slice_stop=content.cursor_position.x
            )
            == 1
        )
        assert screen.get_cursor_position(win) == Point(x=9, y=0)


def test_wrapped_cursor_when_space_starts_visual_line():
    """A space as the first character of a wrapped line must not lose the cursor."""
    # 10 visible chars, then a space that wraps to column 0 of the next row.
    text = "1234567890 "
    with _render_wrapped_buffer(text, width=10, height=4) as (win, screen, _control):
        assert screen.get_cursor_position(win) == Point(x=1, y=1)
        assert win.render_info.cursor_position == Point(x=1, y=1)

    # Single-row window (TextArea multiline=False): scroll to the wrapped row
    # instead of reporting the cursor at (0, 0) on the previous visual line.
    with _render_wrapped_buffer(text, width=10, height=1) as (win, screen, _control):
        assert win.vertical_scroll_2 == 1
        assert screen.get_cursor_position(win) == Point(x=1, y=0)


def test_wrapped_cursor_space_at_end_of_visual_line_does_not_shift():
    """Space just before the wrap point (last column) keeps a stable cursor."""
    text = "123456789 a"
    with _render_wrapped_buffer(text, width=10, height=4) as (win, screen, _control):
        assert screen.get_cursor_position(win) == Point(x=1, y=1)


def test_wrapped_cursor_with_prompt_and_leading_wrapped_space():
    """BeforeInput prompt plus a wrapped leading space (issue #2071)."""
    # Prompt ">>> " (4) + "123456" (6) fills width 10; trailing space wraps.
    text = "123456 "
    with _render_wrapped_buffer(text, width=10, height=4, prompt=">>> ") as (
        win,
        screen,
        _control,
    ):
        assert screen.get_cursor_position(win) == Point(x=1, y=1)

    with _render_wrapped_buffer(text, width=10, height=1, prompt=">>> ") as (
        win,
        screen,
        _control,
    ):
        assert win.vertical_scroll_2 == 1
        assert screen.get_cursor_position(win) == Point(x=1, y=0)


def test_wrapped_cursor_multiple_wraps_with_leading_spaces():
    """Cursor stays on the last wrapped row after several wrap-leading spaces."""
    text = "aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa "
    with _render_wrapped_buffer(text, width=10, height=8) as (win, screen, _control):
        assert screen.get_cursor_position(win) == Point(x=4, y=4)


def test_wrapped_cursor_with_line_prefix_at_wrap_boundary():
    """Window get_line_prefix (PromptSession-style) at an exact wrap boundary."""

    def get_line_prefix(lineno: int, wrap_count: int):
        if wrap_count == 0:
            return ">>> "
        return ""

    buf = Buffer(document=Document("123456", 6), multiline=False)
    buf._load_history_task = True
    control = BufferControl(buffer=buf, include_default_input_processors=False)
    win = Window(content=control, wrap_lines=True, get_line_prefix=get_line_prefix)
    with create_pipe_input() as inp:
        app = Application(layout=Layout(win), output=DummyOutput(), input=inp)
        with set_app(app):
            content = control.create_content(10, 4)
            # Prefix 4 + 6 chars = width 10; cursor cell wraps to the next row.
            assert (
                content.get_height_for_line(
                    0, 10, get_line_prefix, slice_stop=content.cursor_position.x
                )
                == 2
            )
            screen = Screen()
            win.write_to_screen(
                screen,
                MouseHandlers(),
                WritePosition(0, 0, 10, 4),
                "",
                False,
                None,
            )
            assert screen.get_cursor_position(win) == Point(x=0, y=1)
