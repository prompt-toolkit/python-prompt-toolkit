from __future__ import annotations

import re

import pytest

from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.document import Document
from prompt_toolkit.selection import PasteMode, SelectionType


@pytest.fixture
def document():
    return Document(
        "line 1\n" + "line 2\n" + "line 3\n" + "line 4\n", len("line 1\n" + "lin")
    )


def test_current_char(document):
    assert document.current_char == "e"
    assert document.char_before_cursor == "n"


def test_text_before_cursor(document):
    assert document.text_before_cursor == "line 1\nlin"


def test_text_after_cursor(document):
    assert document.text_after_cursor == "e 2\n" + "line 3\n" + "line 4\n"


def test_lines(document):
    assert document.lines == ["line 1", "line 2", "line 3", "line 4", ""]


def test_line_count(document):
    assert document.line_count == 5


def test_current_line_before_cursor(document):
    assert document.current_line_before_cursor == "lin"


def test_current_line_after_cursor(document):
    assert document.current_line_after_cursor == "e 2"


def test_current_line(document):
    assert document.current_line == "line 2"


def test_cursor_position(document):
    assert document.cursor_position_row == 1
    assert document.cursor_position_col == 3

    d = Document("", 0)
    assert d.cursor_position_row == 0
    assert d.cursor_position_col == 0


def test_translate_index_to_position(document):
    pos = document.translate_index_to_position(len("line 1\nline 2\nlin"))

    assert pos[0] == 2
    assert pos[1] == 3

    pos = document.translate_index_to_position(0)
    assert pos == (0, 0)


def test_is_cursor_at_the_end(document):
    assert Document("hello", 5).is_cursor_at_the_end
    assert not Document("hello", 4).is_cursor_at_the_end


def test_get_word_before_cursor_with_whitespace_and_pattern():
    text = "foobar "
    document = Document(text=text, cursor_position=len(text))

    assert document.get_word_before_cursor() == ""

    _FIND_WORD_RE = re.compile(r"([a-zA-Z0-9_]+|[^a-zA-Z0-9_\s]+)")
    assert document.get_word_before_cursor(pattern=_FIND_WORD_RE) == ""


@pytest.mark.parametrize(
    "text,cursor_position", [("", 0), ("abcd", 0), ("abcd", 2), ("abcd", 4)]
)
@pytest.mark.parametrize(
    "paste_mode", [PasteMode.EMACS, PasteMode.VI_BEFORE, PasteMode.VI_AFTER]
)
def test_paste_empty_character_data(text, cursor_position, paste_mode):
    document = Document(text, cursor_position)

    result = document.paste_clipboard_data(ClipboardData(), paste_mode=paste_mode)

    assert result.text == text
    assert result.cursor_position == cursor_position


@pytest.mark.parametrize(
    "paste_mode,text,cursor_position",
    [(PasteMode.VI_BEFORE, "\nabc", 0), (PasteMode.VI_AFTER, "abc\n", 4)],
)
def test_paste_empty_line_data(paste_mode, text, cursor_position):
    result = Document("abc", 1).paste_clipboard_data(
        ClipboardData("", SelectionType.LINES), paste_mode=paste_mode
    )

    assert result.text == text
    assert result.cursor_position == cursor_position
