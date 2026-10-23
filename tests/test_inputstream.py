from __future__ import annotations

import pytest

from prompt_toolkit.input.vt100_parser import Vt100Parser
from prompt_toolkit.keys import Keys


class _ProcessorMock:
    def __init__(self):
        self.keys = []

    def feed_key(self, key_press):
        self.keys.append(key_press)


@pytest.fixture
def processor():
    return _ProcessorMock()


@pytest.fixture
def stream(processor):
    return Vt100Parser(processor.feed_key)


def test_control_keys(processor, stream):
    stream.feed("\x01\x02\x10")

    assert len(processor.keys) == 3
    assert processor.keys[0].key == Keys.ControlA
    assert processor.keys[1].key == Keys.ControlB
    assert processor.keys[2].key == Keys.ControlP
    assert processor.keys[0].data == "\x01"
    assert processor.keys[1].data == "\x02"
    assert processor.keys[2].data == "\x10"


def test_arrows(processor, stream):
    stream.feed("\x1b[A\x1b[B\x1b[C\x1b[D")

    assert len(processor.keys) == 4
    assert processor.keys[0].key == Keys.Up
    assert processor.keys[1].key == Keys.Down
    assert processor.keys[2].key == Keys.Right
    assert processor.keys[3].key == Keys.Left
    assert processor.keys[0].data == "\x1b[A"
    assert processor.keys[1].data == "\x1b[B"
    assert processor.keys[2].data == "\x1b[C"
    assert processor.keys[3].data == "\x1b[D"


def test_escape(processor, stream):
    stream.feed("\x1bhello")

    assert len(processor.keys) == 1 + len("hello")
    assert processor.keys[0].key == Keys.Escape
    assert processor.keys[1].key == "h"
    assert processor.keys[0].data == "\x1b"
    assert processor.keys[1].data == "h"


def test_special_double_keys(processor, stream):
    stream.feed("\x1b[1;3D")  # Should both send escape and left.

    assert len(processor.keys) == 2
    assert processor.keys[0].key == Keys.Escape
    assert processor.keys[1].key == Keys.Left
    assert processor.keys[0].data == "\x1b[1;3D"
    assert processor.keys[1].data == ""


def test_flush_1(processor, stream):
    # Send left key in two parts without flush.
    stream.feed("\x1b")
    stream.feed("[D")

    assert len(processor.keys) == 1
    assert processor.keys[0].key == Keys.Left
    assert processor.keys[0].data == "\x1b[D"


def test_flush_2(processor, stream):
    # Send left key with a 'Flush' in between.
    # The flush should make sure that we process everything before as-is,
    # with makes the first part just an escape character instead.
    stream.feed("\x1b")
    stream.flush()
    stream.feed("[D")

    assert len(processor.keys) == 3
    assert processor.keys[0].key == Keys.Escape
    assert processor.keys[1].key == "["
    assert processor.keys[2].key == "D"

    assert processor.keys[0].data == "\x1b"
    assert processor.keys[1].data == "["
    assert processor.keys[2].data == "D"


def test_meta_arrows(processor, stream):
    stream.feed("\x1b\x1b[D")

    assert len(processor.keys) == 2
    assert processor.keys[0].key == Keys.Escape
    assert processor.keys[1].key == Keys.Left


def test_control_square_close(processor, stream):
    stream.feed("\x1dC")

    assert len(processor.keys) == 2
    assert processor.keys[0].key == Keys.ControlSquareClose
    assert processor.keys[1].key == "C"


def test_invalid(processor, stream):
    # Invalid sequence that has at two characters in common with other
    # sequences.
    stream.feed("\x1b[*")

    assert len(processor.keys) == 3
    assert processor.keys[0].key == Keys.Escape
    assert processor.keys[1].key == "["
    assert processor.keys[2].key == "*"


def test_cpr_response(processor, stream):
    stream.feed("a\x1b[40;10Rb")
    assert len(processor.keys) == 3
    assert processor.keys[0].key == "a"
    assert processor.keys[1].key == Keys.CPRResponse
    assert processor.keys[2].key == "b"


def test_cpr_response_2(processor, stream):
    # Make sure that the newline is not included in the CPR response.
    stream.feed("\x1b[40;1R\n")
    assert len(processor.keys) == 2
    assert processor.keys[0].key == Keys.CPRResponse
    assert processor.keys[1].key == Keys.ControlJ


def _key_names(value):
    "Flatten an ANSI_SEQUENCES value into the key names it resolves to."
    if isinstance(value, tuple):
        return [k.name for k in value]
    return [value.name if hasattr(value, "name") else str(value)]


@pytest.mark.parametrize(
    "final,direction",
    [("A", "Up"), ("B", "Down"), ("C", "Right"), ("D", "Left")],
)
def test_modified_cursor_keys_keep_their_direction(final, direction):
    """CSI 1 ; <modifier> A is cursor-up at every modifier level, and so on for B/C/D.

    Regression test for https://github.com/prompt-toolkit/python-prompt-toolkit/issues/2092
    where A and B were transposed at modifiers 4, 6, 7 and 8 but correct at 2, 3, 5 and 9,
    so Ctrl+Shift+Up moved the cursor down.
    """
    from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES

    for modifier in range(2, 17):
        value = ANSI_SEQUENCES.get(f"\x1b[1;{modifier}{final}")
        if value is None:
            continue
        names = _key_names(value)
        assert any(direction in name for name in names), (
            f"\\x1b[1;{modifier}{final} should name {direction}, got {names}"
        )


@pytest.mark.parametrize("number,direction", [(5, "PageUp"), (6, "PageDown")])
def test_modified_page_keys_keep_their_direction(number, direction):
    """CSI 5 ; <modifier> ~ is PageUp and CSI 6 ; <modifier> ~ is PageDown, at every level."""
    from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES

    for modifier in range(2, 17):
        value = ANSI_SEQUENCES.get(f"\x1b[{number};{modifier}~")
        if value is None:
            continue
        names = _key_names(value)
        assert any(direction in name for name in names), (
            f"\\x1b[{number};{modifier}~ should name {direction}, got {names}"
        )
