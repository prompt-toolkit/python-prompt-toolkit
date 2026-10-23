from __future__ import annotations

import pytest

from prompt_toolkit.buffer import Buffer


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


def test_undo_redo_with_default_binding_snapshots(_buffer):
    for char in "abc":
        _buffer.save_to_undo_stack()
        _buffer.insert_text(char)

    for expected in ("ab", "a"):
        _buffer.save_to_undo_stack()
        _buffer.undo()
        assert _buffer.text == expected

    for expected in ("ab", "abc"):
        _buffer.save_to_undo_stack()
        _buffer.redo()
        assert _buffer.text == expected


def test_edit_after_undo_clears_redo_stack(_buffer):
    for char in "abc":
        _buffer.save_to_undo_stack()
        _buffer.insert_text(char)

    _buffer.save_to_undo_stack()
    _buffer.undo()
    assert _buffer.text == "ab"

    _buffer.save_to_undo_stack()
    _buffer.insert_text("x")
    _buffer.save_to_undo_stack()
    _buffer.redo()

    assert _buffer.text == "abx"


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
