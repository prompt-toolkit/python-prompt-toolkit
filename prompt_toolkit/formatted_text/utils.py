"""
Utilities for manipulating formatted text.

When ``to_formatted_text`` has been called, we get a list of ``(style, text)``
tuples. This file contains functions for manipulating such a list.
"""
from typing import Iterable, List, cast

from prompt_toolkit.utils import get_cwidth

from .base import (
    AnyFormattedText,
    OneStyleAndTextTuple,
    StyleAndTextTuples,
    merge_formatted_text,
    to_formatted_text,
)

__all__ = [
    # Higher level formatted-text operations.
    "formatted_text_len",
    "formatted_text_width",
    "formatted_text_to_text",
    "formatted_text_split_lines",
    "formatted_text_indent",
    "formatted_text_strip",
    # Lower-level fragment operations.
    "fragment_list_len",
    "fragment_list_width",
    "fragment_list_to_text",
    "split_lines",
]


def formatted_text_len(text: AnyFormattedText) -> int:
    """
    Return the amount of characters in this formatted text.
    """
    return fragment_list_len(to_formatted_text(text))


def formatted_text_width(text: AnyFormattedText) -> int:
    """
    Return the amount of space this formatted text would occupy when printing
    on a terminal (this takes double width characters into account).
    """
    return fragment_list_width(to_formatted_text(text))


def formatted_text_to_text(text: AnyFormattedText) -> str:
    """
    Turn formatted text back into plain text.
    """
    return fragment_list_to_text(to_formatted_text(text))


def formatted_text_split_lines(text: AnyFormattedText) -> List[StyleAndTextTuples]:
    """
    Take any formatted text, split the lines and turn it into a list of
    formatted text objects.
    """
    return list(split_lines(to_formatted_text(text)))


def formatted_text_indent(
    text: AnyFormattedText,
    prefix: AnyFormattedText = "",
    indent_first_line: bool = True,
) -> StyleAndTextTuples:
    """
    Insert the given prefix before every line of text.
    """
    lines = split_lines(to_formatted_text(text))

    result = []
    for i, line in enumerate(lines):
        if i > 0 or (indent_first_line and i == 0):
            line = to_formatted_text(merge_formatted_text([prefix, line]))
        result.extend(line)
    return result


def formatted_text_strip(text: AnyFormattedText) -> StyleAndTextTuples:
    """
    Strip whitespace around formatted text.
    """
    # TODO


# ---


def fragment_list_len(fragments: StyleAndTextTuples) -> int:
    """
    Return the amount of characters in this text fragment list.

    :param fragments: List of ``(style_str, text)`` or
        ``(style_str, text, mouse_handler)`` tuples.
    """
    ZeroWidthEscape = "[ZeroWidthEscape]"
    return sum(len(item[1]) for item in fragments if ZeroWidthEscape not in item[0])


def fragment_list_width(fragments: StyleAndTextTuples) -> int:
    """
    Return the character width of this text fragment list.
    (Take double width characters into account.)

    :param fragments: List of ``(style_str, text)`` or
        ``(style_str, text, mouse_handler)`` tuples.
    """
    ZeroWidthEscape = "[ZeroWidthEscape]"
    return sum(
        get_cwidth(c)
        for item in fragments
        for c in item[1]
        if ZeroWidthEscape not in item[0]
    )


def fragment_list_to_text(fragments: StyleAndTextTuples) -> str:
    """
    Concatenate all the text parts again.

    :param fragments: List of ``(style_str, text)`` or
        ``(style_str, text, mouse_handler)`` tuples.
    """
    ZeroWidthEscape = "[ZeroWidthEscape]"
    return "".join(item[1] for item in fragments if ZeroWidthEscape not in item[0])


def split_lines(fragments: StyleAndTextTuples) -> Iterable[StyleAndTextTuples]:
    """
    Take a single list of (style_str, text) tuples and yield one such list for each
    line. Just like str.split, this will yield at least one item.

    :param fragments: List of (style_str, text) or (style_str, text, mouse_handler)
                      tuples.
    """
    line: StyleAndTextTuples = []

    for style, string, *mouse_handler in fragments:
        parts = string.split("\n")

        for part in parts[:-1]:
            if part:
                line.append(cast(OneStyleAndTextTuple, (style, part, *mouse_handler)))
            yield line
            line = []

        line.append(cast(OneStyleAndTextTuple, (style, parts[-1], *mouse_handler)))

    # Always yield the last line, even when this is an empty line. This ensures
    # that when `fragments` ends with a newline character, an additional empty
    # line is yielded. (Otherwise, there's no way to differentiate between the
    # cases where `fragments` does and doesn't end with a newline.)
    yield line
