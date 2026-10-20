from __future__ import annotations

import pytest

from prompt_toolkit.document import Document
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.processors import (
    HighlightMatchingBracketProcessor,
    TransformationInput,
)


@pytest.mark.parametrize("cursor_position", [0, 2])
@pytest.mark.parametrize("prefix", ["", ">> "])
def test_matching_bracket_cursor_style_uses_source_row_and_column(
    cursor_position, prefix
):
    document = Document("(\n)", cursor_position=cursor_position)
    processor = HighlightMatchingBracketProcessor()
    for lineno, line in enumerate(document.lines):
        result = processor.apply_transformation(
            TransformationInput(
                buffer_control=BufferControl(),
                document=document,
                lineno=lineno,
                source_to_display=lambda i: i + len(prefix),
                fragments=[("", prefix + line)],
                width=80,
                height=24,
            )
        )
        style = result.fragments[len(prefix)][0]
        if lineno == document.cursor_position_row:
            assert "class:matching-bracket.cursor" in style
            assert "class:matching-bracket.other" not in style
        else:
            assert "class:matching-bracket.other" in style
            assert "class:matching-bracket.cursor" not in style


@pytest.mark.parametrize("text", ["()", "(\n)"])
@pytest.mark.parametrize("prefix", ["", ">> "])
def test_matching_brackets_after_closing_bracket_keep_other_style(text, prefix):
    document = Document(text, cursor_position=len(text))
    processor = HighlightMatchingBracketProcessor()
    styles = []
    for lineno, line in enumerate(document.lines):
        result = processor.apply_transformation(
            TransformationInput(
                buffer_control=BufferControl(),
                document=document,
                lineno=lineno,
                source_to_display=lambda i: i + len(prefix),
                fragments=[("", prefix + line)],
                width=80,
                height=24,
            )
        )
        styles.extend(style for style, char in result.fragments if char in "()")
    assert len(styles) == 2
    assert all("class:matching-bracket.other" in style for style in styles)
    assert all("class:matching-bracket.cursor" not in style for style in styles)
