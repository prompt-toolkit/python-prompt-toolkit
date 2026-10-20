from __future__ import annotations

import io

from prompt_toolkit.output.vt100 import (
    Vt100_Output,
    _256_colors,
    _get_closest_ansi_color,
)


def test_get_closest_ansi_color():
    # White
    assert _get_closest_ansi_color(255, 255, 255) == "ansiwhite"
    assert _get_closest_ansi_color(250, 250, 250) == "ansiwhite"

    # Black
    assert _get_closest_ansi_color(0, 0, 0) == "ansiblack"
    assert _get_closest_ansi_color(5, 5, 5) == "ansiblack"

    # Green
    assert _get_closest_ansi_color(0, 255, 0) == "ansibrightgreen"
    assert _get_closest_ansi_color(10, 255, 0) == "ansibrightgreen"
    assert _get_closest_ansi_color(0, 255, 10) == "ansibrightgreen"

    assert _get_closest_ansi_color(220, 220, 100) == "ansiyellow"


def test_256_colors():
    # 6x6x6 cube
    assert _256_colors[(0, 0, 0)] == 16  # First color in cube
    assert _256_colors[(255, 255, 255)] == 231  # Last color in cube
    assert _256_colors[(95, 95, 95)] == 59  # Verifies a color between the boundaries

    # Grayscale
    assert _256_colors[(8, 8, 8)] == 232  # First grayscale level
    assert _256_colors[(238, 238, 238)] == 255  # Last grayscale level


def _make_output() -> Vt100_Output:
    return Vt100_Output(io.StringIO(), lambda: None, term="xterm")


def test_write_strips_c1_controls():
    # 8-bit CSI/OSC/ST must not reach the terminal, same as ESC.
    output = _make_output()
    output.write("a\x1b[31mb\x9b31mc\x9d0;x\x9cd\u2500")
    assert output._buffer == ["a?[31mb?31mc?0;x?d\u2500"]


def test_set_title_strips_c1_controls():
    output = _make_output()
    output.set_title("title\x9c\x9b2J")
    assert output._buffer == ["\x1b]2;title2J\x07"]
