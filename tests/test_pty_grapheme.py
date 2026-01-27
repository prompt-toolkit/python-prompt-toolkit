r"""PTY-based grapheme clustering tests.

Tests that cursor movement and editing operations respect grapheme cluster
boundaries for complex Unicode sequences like emoji with ZWJ, skin tones,
combining characters, and regional indicators.

The pty helpers are designed for this particular test, while improving support
for grapheme clustering, so many errors were only found by interactive testing,
but systematic to test--just move the cursor, inserting, and erasing text
and test the desired result.
"""

from __future__ import annotations

import os
import platform
import time

import pytest
from pty_accessories import extract_output, pty_session, read_until_marker

pytestmark = pytest.mark.skipif(
    platform.system() == "Windows", reason="PTY tests not supported on Windows"
)

# Key sequences
LEFT = "\x1b[D"  # cursor left
RIGHT = "\x1b[C"  # cursor right
HOME = "\x1b[H"  # home
BS = "\x7f"  # backspace
DEL = "\x1b[3~"  # forward delete
ENTER = "\r"

# Grapheme clusters covering major Unicode complexity classes
GRAPHEMES = [
    # U+1F468 U+200D U+1F469 U+200D U+1F467
    (
        "\U0001f468\u200d\U0001f469\u200d\U0001f467",
        "zwj_family",
    ),
    # U+2764 U+FE0F (VS-16)
    ("\u2764\ufe0f", "vs16_heart"),
    # U+1F1E8 U+1F1E6 (C+A regional indicators)
    ("\U0001f1e8\U0001f1e6", "flag_ca"),
    # U+0065 U+0301
    ("e\u0301", "combining_acute"),
    # U+1100 U+1161
    ("\u1100\u1161", "hangul_lv"),
    # Devanagari conjunct
    ("\u0915\u094d\u0937\u093f", "devanagari"),
    # U+1F44B U+1F3FB
    ("\U0001f44b\U0001f3fb", "skin_tone"),
]


@pytest.fixture
def repl_script():
    return os.path.join(os.path.dirname(__file__), "pty_repl.py")


@pytest.mark.parametrize("grapheme,name", GRAPHEMES)
def test_backspace_deletes_grapheme(repl_script, grapheme, name):
    """Type 3 graphemes, backspace twice, verify 1 remains."""
    with pty_session(repl_script, rows=3, cols=40) as fd:
        os.write(fd, (grapheme * 3).encode())
        time.sleep(0.1)
        os.write(fd, (BS * 2 + ENTER).encode())
        assert extract_output(read_until_marker(fd, ":END")) == grapheme


@pytest.mark.parametrize("grapheme,name", GRAPHEMES)
def test_cursor_movement_respects_grapheme(repl_script, grapheme, name):
    """Type 3 graphemes, LEFT, insert 'x' -> pattern is 2+x+1."""
    with pty_session(repl_script, rows=3, cols=40) as fd:
        os.write(fd, (grapheme * 3).encode())
        time.sleep(0.1)
        os.write(fd, (LEFT + "x" + ENTER).encode())
        assert (
            extract_output(read_until_marker(fd, ":END"))
            == grapheme * 2 + "x" + grapheme
        )


@pytest.mark.parametrize("grapheme,name", GRAPHEMES)
def test_forward_delete_removes_grapheme(repl_script, grapheme, name):
    """Type 3 graphemes, HOME, DELETE -> 2 remain."""
    with pty_session(repl_script, rows=3, cols=40) as fd:
        os.write(fd, (grapheme * 3).encode())
        time.sleep(0.1)
        os.write(fd, (HOME + DEL + ENTER).encode())
        assert extract_output(read_until_marker(fd, ":END")) == grapheme * 2


@pytest.mark.parametrize(
    "grapheme,name", [GRAPHEMES[0], GRAPHEMES[2]]
)  # ZWJ family, CA flag
def test_grapheme_in_tiny_window(repl_script, grapheme, name):
    """Type 10 graphemes in 10-col window, backspace 5, verify 5 remain."""
    with pty_session(repl_script, rows=3, cols=10) as fd:
        os.write(fd, (grapheme * 10).encode())
        time.sleep(0.2)
        os.write(fd, (BS * 5 + ENTER).encode())
        time.sleep(0.2)
        assert (
            extract_output(read_until_marker(fd, ":END", timeout=10.0)) == grapheme * 5
        )
