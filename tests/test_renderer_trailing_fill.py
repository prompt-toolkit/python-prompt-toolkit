from types import SimpleNamespace

from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.layout.screen import Char, Screen
from prompt_toolkit.output import ColorDepth, DummyOutput
from prompt_toolkit.renderer import (
    _output_screen_diff,
    _StyleStringHasStyleCache,
    _StyleStringToAttrsCache,
)
from prompt_toolkit.styles import DummyStyleTransformation, Style


class RecordingOutput(DummyOutput):
    def __init__(self) -> None:
        self.writes: list[str] = []
        self.attributes = []
        self.erase_end_of_line_calls = 0

    def write(self, data: str) -> None:
        self.writes.append(data)

    def set_attributes(self, attrs, color_depth) -> None:
        self.attributes.append(attrs)

    def erase_end_of_line(self) -> None:
        self.erase_end_of_line_calls += 1


def render_screen(
    screen: Screen, style: Style, previous_screen: Screen | None, previous_width: int
) -> RecordingOutput:
    attrs = _StyleStringToAttrsCache(
        style.get_attrs_for_style_str, DummyStyleTransformation()
    )
    output = RecordingOutput()
    _output_screen_diff(
        SimpleNamespace(layout=SimpleNamespace(current_window=object())),
        output,
        screen,
        Point(x=0, y=0),
        ColorDepth.DEPTH_8_BIT,
        previous_screen,
        None,
        False,
        False,
        attrs,
        _StyleStringHasStyleCache(attrs),
        Size(rows=1, columns=8),
        previous_width,
    )
    return output


def make_filled_screen(fill_style: str = "class:fill") -> Screen:
    screen = Screen()
    screen.height = 1
    screen.width = 8
    screen.data_buffer[0][0] = Char(">")
    for column in range(1, 8):
        screen.data_buffer[0][column] = Char(" ", fill_style)
    return screen


def test_styled_trailing_fill_uses_erase_to_end_of_line_on_resize() -> None:
    screen = make_filled_screen()
    style = Style.from_dict({"fill": "bg:ansiblue"})

    output = render_screen(screen, style, Screen(), previous_width=12)

    assert output.writes == [">"]
    assert output.erase_end_of_line_calls == 1
    assert output.attributes[-1].bgcolor == "ansiblue"


def test_unchanged_trailing_fill_is_not_erased_again() -> None:
    screen = make_filled_screen()
    style = Style.from_dict({"fill": "bg:ansiblue"})

    output = render_screen(screen, style, make_filled_screen(), previous_width=8)

    assert output.writes == []
    assert output.erase_end_of_line_calls == 0


def test_underlined_trailing_spaces_keep_the_literal_space_rendering() -> None:
    screen = make_filled_screen()
    style = Style.from_dict({"fill": "bg:ansiblue underline"})

    output = render_screen(screen, style, Screen(), previous_width=12)

    assert "".join(output.writes).replace("\r", "") == ">" + " " * 7
    assert output.erase_end_of_line_calls == 0
