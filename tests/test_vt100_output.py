from __future__ import annotations

from prompt_toolkit.output.vt100 import _256_colors, _get_closest_ansi_color


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
