from __future__ import annotations

import asyncio

import pytest

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import set_app
from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput


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


class _AlwaysSuggest(AutoSuggest):
    """Auto suggester that records the documents it was called with."""

    def __init__(self) -> None:
        self.documents: list[Document] = []

    def get_suggestion(self, buffer: Buffer, document: Document) -> Suggestion:
        self.documents.append(document)
        return Suggestion(" suggestion")


def test_auto_suggest_after_delete():
    """
    A suggestion should be generated after deleting text as well, not only
    after inserting text.
    """

    async def run() -> None:
        suggester = _AlwaysSuggest()
        buff = Buffer(auto_suggest=suggester)
        app = Application(input=DummyInput(), output=DummyOutput())

        with set_app(app):
            # Typing generates a suggestion.
            buff.insert_text("hello")
            await asyncio.sleep(0.1)
            assert buff.suggestion is not None
            assert buff.suggestion.text == " suggestion"
            assert [d.text for d in suggester.documents] == ["hello"]

            # Deleting a character clears the suggestion, but a new one
            # should be generated for the remaining text.
            buff.delete_before_cursor()
            await asyncio.sleep(0.1)
            assert buff.text == "hell"
            assert buff.suggestion is not None
            assert buff.suggestion.text == " suggestion"
            assert suggester.documents[-1].text == "hell"

    asyncio.run(run())
