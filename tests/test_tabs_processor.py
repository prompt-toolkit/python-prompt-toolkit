from __future__ import annotations

import pytest

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import fragment_list_to_text
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.processors import TabsProcessor, TransformationInput


@pytest.mark.parametrize(
    "text, expected, mappings",
    [
        ("a\tb", "a   b", [0, 1, 4, 5]),
        ("\x01\tb", "\x01  b", [0, 1, 3, 4]),
        ("\x80\tb", "\x80    b", [0, 1, 5, 6]),
        ("界\tb", "界  b", [0, 1, 3, 4]),
        ("界界\tb", "界界    b", [0, 1, 2, 6, 7]),
        ("e\u0301\tb", "e\u0301   b", [0, 1, 2, 5, 6]),
        ("界\t界\tb", "界  界  b", [0, 1, 3, 4, 6, 7]),
    ],
)
def test_tabs_follow_terminal_columns(text, expected, mappings):
    result = TabsProcessor(tabstop=4, char1=" ", char2=" ").apply_transformation(
        TransformationInput(
            buffer_control=BufferControl(),
            document=Document(text),
            lineno=0,
            source_to_display=lambda i: i,
            fragments=[("", text)],
            width=80,
            height=24,
        )
    )
    assert fragment_list_to_text(result.fragments) == expected
    assert [result.source_to_display(i) for i in range(len(text) + 1)] == mappings
    for source, display in enumerate(mappings):
        assert result.display_to_source(display) == source
    for source, char in enumerate(text):
        if char == "\t":
            for display in range(mappings[source], mappings[source + 1]):
                assert result.display_to_source(display) == source


@pytest.mark.parametrize("escape", ["\x1b[31m", "\x1b]0;title\tvalue\x07"])
def test_tabs_preserve_zero_width_escapes(escape):
    result = TabsProcessor(tabstop=4, char1=" ", char2=" ").apply_transformation(
        TransformationInput(
            buffer_control=BufferControl(),
            document=Document("a\tb"),
            lineno=0,
            source_to_display=lambda i: i,
            fragments=[("", "a"), ("[ZeroWidthEscape]", escape), ("", "\tb")],
            width=80,
            height=24,
        )
    )
    assert fragment_list_to_text(result.fragments) == "a   b"
    assert (
        "".join(
            text for style, text in result.fragments if "[ZeroWidthEscape]" in style
        )
        == escape
    )
    assert [result.source_to_display(i) for i in range(4)] == [0, 1, 4, 5]
    assert [result.display_to_source(i) for i in range(6)] == [0, 1, 1, 1, 2, 3]
