"""
Tests for `prompt_toolkit.renderer._output_screen_diff`.
"""

from __future__ import annotations

from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.layout.screen import Char, Screen
from prompt_toolkit.output import ColorDepth, DummyOutput
from prompt_toolkit.renderer import (
    _output_screen_diff,
    _StyleStringHasStyleCache,
    _StyleStringToAttrsCache,
)
from prompt_toolkit.styles import DummyStyleTransformation, Style


class _CapturingOutput(DummyOutput):
    "Like `DummyOutput`, but remembers everything written to it."

    def __init__(self) -> None:
        self.written: list[str] = []

    def write(self, data: str) -> None:
        self.written.append(data)


def _render(new_row_cells):
    """
    Render a single ten-column, one-row screen against a blank previous
    screen, given the (column, char, style) cells to put in the new row.
    Returns the concatenation of everything that got written to the output.
    """
    style = Style.from_dict({})
    attrs_for_style_string = _StyleStringToAttrsCache(
        style.get_attrs_for_style_str, DummyStyleTransformation()
    )
    style_string_has_style = _StyleStringHasStyleCache(attrs_for_style_string)

    previous_screen = Screen()
    previous_screen.width = 10
    previous_screen.height = 1

    screen = Screen()
    screen.width = 10
    screen.height = 1
    for column, char, cell_style in new_row_cells:
        screen.data_buffer[0][column] = Char(char, cell_style)

    output = _CapturingOutput()

    _output_screen_diff(
        app=None,
        output=output,
        screen=screen,
        current_pos=Point(x=0, y=0),
        color_depth=ColorDepth.DEPTH_1_BIT,
        previous_screen=previous_screen,
        last_style=None,
        is_done=True,
        full_screen=False,
        attrs_for_style_string=attrs_for_style_string,
        style_string_has_style=style_string_has_style,
        size=Size(rows=1, columns=10),
        previous_width=10,
    )
    return "".join(output.written)


def test_blank_row_does_not_redraw_a_space():
    """
    A line that never got any real content (just the default blank cell at
    column 0) shouldn't have a space written for it, even on the first
    render where its style differs from the previous screen's default.
    """
    written = _render([(0, " ", "")])
    assert " " not in written


def test_content_at_column_zero_is_still_drawn():
    """
    A line whose only visible character happens to sit at column 0 must
    still be drawn. This is the case a naive "skip column 0 when the row's
    max index is 0" fix would break, since a lone character at column 0
    also has a max index of 0.
    """
    written = _render([(0, "$", "")])
    assert "$" in written


def test_content_after_column_zero_is_still_drawn():
    """
    A line with real content beyond column 0 is unaffected by the blank-row
    check either way, but is worth pinning down alongside the two cases
    above.
    """
    written = _render([(0, " ", ""), (1, "$", "")])
    assert "$" in written
