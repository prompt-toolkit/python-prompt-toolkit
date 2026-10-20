from __future__ import annotations

import io

import pytest

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML, to_formatted_text


@pytest.mark.parametrize(
    "markup, expected",
    [
        ("<!-- hidden -->", []),
        ("before<!-- hidden -->after", [("", "before"), ("", "after")]),
        (
            "<b>before<!-- <i>hidden</i> -->after</b>",
            [("class:b", "before"), ("class:b", "after")],
        ),
        (
            '<style fg="ansired"><!-- hidden --><b>text</b></style>after',
            [("class:b fg:ansired", "text"), ("", "after")],
        ),
        ("<?note hidden?>visible", [("", "visible")]),
        (
            "<b>before<?note hidden?>after</b>",
            [("class:b", "before"), ("class:b", "after")],
        ),
        ("<![CDATA[a < b & c]]>", [("", "a < b & c")]),
        (
            '<b fg="ansired"><![CDATA[<i>literal</i>]]></b>after',
            [("class:b fg:ansired", "<i>literal</i>"), ("", "after")],
        ),
        (
            "<b>before<![CDATA[ & ]]><!-- hidden -->after</b>",
            [("class:b", "before"), ("class:b", " & "), ("class:b", "after")],
        ),
    ],
)
def test_html_non_element_nodes(markup, expected):
    assert to_formatted_text(HTML(markup)) == expected


def test_print_html_with_comments_and_cdata():
    output = io.StringIO()
    print_formatted_text(
        HTML("<b>Result: <!-- internal note --><![CDATA[x < 3]]></b>"),
        file=output,
    )
    assert output.getvalue() == "Result: x < 3\r\n"
