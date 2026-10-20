from __future__ import annotations

import pytest

from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.margins import NumberedMargin
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Screen, WritePosition


class LinesControl(UIControl):
    def __init__(self, lines):
        self.lines = lines

    def create_content(self, width, height):
        return UIContent(
            get_line=lambda i: [("", self.lines[i])],
            line_count=len(self.lines),
        )


@pytest.mark.parametrize("relative", [False, True])
@pytest.mark.parametrize("side", ["left_margins", "right_margins"])
def test_numbered_margin_renders_empty_content(relative, side):
    margin = NumberedMargin(relative=relative, display_tildes=True)
    window = Window(content=LinesControl([]), **{side: [margin]})
    screen = Screen()
    window.write_to_screen(
        screen, MouseHandlers(), WritePosition(0, 0, 10, 3), "", True, None
    )
    column = 0 if side == "left_margins" else 7
    assert [screen.data_buffer[row][column].char for row in range(3)] == ["~"] * 3


@pytest.mark.parametrize("line_count", [0, 1, 2, 3, 4])
@pytest.mark.parametrize("display_tildes", [False, True])
def test_numbered_margin_fills_only_remaining_rows(line_count, display_tildes):
    margin = NumberedMargin(display_tildes=display_tildes)
    window = Window(content=LinesControl(["text"] * line_count), left_margins=[margin])
    window.write_to_screen(
        Screen(), MouseHandlers(), WritePosition(0, 0, 10, 3), "", True, None
    )
    info = window.render_info
    assert info is not None
    fragments = margin.create_margin(info, 3, 3)
    tilde_rows = sum(text == "~\n" for _, text in fragments)
    assert tilde_rows == (max(0, 3 - line_count) if display_tildes else 0)
    assert sum(text.count("\n") for _, text in fragments) == (
        3 if display_tildes else min(line_count, 3)
    )


def test_numbered_margin_counts_wrapped_screen_rows():
    margin = NumberedMargin(display_tildes=True)
    window = Window(
        content=LinesControl(["abcdefgh"]), left_margins=[margin], wrap_lines=True
    )
    window.write_to_screen(
        Screen(), MouseHandlers(), WritePosition(0, 0, 7, 4), "", True, None
    )
    info = window.render_info
    assert info is not None
    assert info.displayed_lines == [0, 0]
    fragments = margin.create_margin(info, 3, 4)
    assert sum(text == "~\n" for _, text in fragments) == 2
    assert sum(text.count("\n") for _, text in fragments) == 4
