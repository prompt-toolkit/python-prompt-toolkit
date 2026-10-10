from __future__ import annotations

import asyncio

import pytest

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


@pytest.fixture
def _buffer():
    buff = Buffer()
    return buff


def test_initial(_buffer):
    assert _buffer.text == ""
    assert _buffer.cursor_position == 0


def test_insert_text(_buffer):
    _buffer.insert_text("some_text")
    assert _buffer.text == "some_text"
    assert _buffer.cursor_position == len("some_text")


def test_cursor_movement(_buffer):
    _buffer.insert_text("some_text")
    _buffer.cursor_left()
    _buffer.cursor_left()
    _buffer.cursor_left()
    _buffer.cursor_right()
    _buffer.insert_text("A")

    assert _buffer.text == "some_teAxt"
    assert _buffer.cursor_position == len("some_teA")


def test_backspace(_buffer):
    _buffer.insert_text("some_text")
    _buffer.cursor_left()
    _buffer.cursor_left()
    _buffer.delete_before_cursor()

    assert _buffer.text == "some_txt"
    assert _buffer.cursor_position == len("some_t")


def test_cursor_up(_buffer):
    # Cursor up to a line thats longer.
    _buffer.insert_text("long line1\nline2")
    _buffer.cursor_up()

    assert _buffer.document.cursor_position == 5

    # Going up when already at the top.
    _buffer.cursor_up()
    assert _buffer.document.cursor_position == 5

    # Going up to a line that's shorter.
    _buffer.reset()
    _buffer.insert_text("line1\nlong line2")

    _buffer.cursor_up()
    assert _buffer.document.cursor_position == 5


def test_cursor_down(_buffer):
    _buffer.insert_text("line1\nline2")
    _buffer.cursor_position = 3

    # Normally going down
    _buffer.cursor_down()
    assert _buffer.document.cursor_position == len("line1\nlin")

    # Going down to a line that's shorter.
    _buffer.reset()
    _buffer.insert_text("long line1\na\nb")
    _buffer.cursor_position = 3

    _buffer.cursor_down()
    assert _buffer.document.cursor_position == len("long line1\na")


def test_join_next_line(_buffer):
    _buffer.insert_text("line1\nline2\nline3")
    _buffer.cursor_up()
    _buffer.join_next_line()

    assert _buffer.text == "line1\nline2 line3"

    # Test when there is no '\n' in the text
    _buffer.reset()
    _buffer.insert_text("line1")
    _buffer.cursor_position = 0
    _buffer.join_next_line()

    assert _buffer.text == "line1"


def test_newline(_buffer):
    _buffer.insert_text("hello world")
    _buffer.newline()

    assert _buffer.text == "hello world\n"


def test_swap_characters_before_cursor(_buffer):
    _buffer.insert_text("hello world")
    _buffer.cursor_left()
    _buffer.cursor_left()
    _buffer.swap_characters_before_cursor()

    assert _buffer.text == "hello wrold"


def test_common_completion_preserves_styles():
    class StyledCompleter(Completer):
        def get_completions(self, document, complete_event):
            for text, style, selected_style in (
                ("hello", "fg:ansired", "bg:ansigreen"),
                ("help", "fg:ansiblue", "bg:ansiyellow"),
            ):
                yield Completion(
                    text,
                    start_position=-2,
                    style=style,
                    selected_style=selected_style,
                )

    buffer = Buffer(completer=StyledCompleter(), document=Document("he", 2))
    asyncio.run(buffer._async_completer(insert_common_part=True))

    assert buffer.text == "hel"
    assert buffer.complete_state is not None
    completions = buffer.complete_state.completions
    assert [(c.text, c.style, c.selected_style) for c in completions] == [
        ("lo", "fg:ansired", "bg:ansigreen"),
        ("p", "fg:ansiblue", "bg:ansiyellow"),
    ]
    buffer.go_to_completion(0)
    assert buffer.text == "hello"
    buffer.go_to_completion(1)
    assert buffer.text == "help"
