r"""PTY-based tests for terminal size and termios state."""

from __future__ import annotations

import fcntl
import os
import platform
import struct
import termios
import time

import pytest
from pty_accessories import extract_output, pty_session, read_until_marker

pytestmark = pytest.mark.skipif(
    platform.system() == "Windows", reason="PTY tests not supported on Windows"
)


@pytest.fixture
def repl_script():
    return os.path.join(os.path.dirname(__file__), "pty_repl.py")


def _setwinsize(fd: int, rows: int, cols: int) -> None:
    TIOCSWINSZ = getattr(termios, "TIOCSWINSZ", -2146929561)
    fcntl.ioctl(fd, TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def _get_size(fd: int) -> tuple[int, int]:
    # manage call and reply of 'SIZE' command to pty_repl.py
    os.write(fd, b"SIZE\r")
    size_str = extract_output(read_until_marker(fd, ":END"), "SIZE:", ":END")
    r, c = size_str.split("x")
    return int(r), int(c)


@pytest.mark.parametrize("rows,cols", [(25, 80), (3, 10), (100, 200), (1, 1)])
def test_size_detection(repl_script, rows, cols):
    with pty_session(repl_script, rows=rows, cols=cols) as fd:
        assert _get_size(fd) == (rows, cols)


def test_dynamic_size_change(repl_script):
    with pty_session(repl_script, rows=24, cols=80) as fd:
        assert _get_size(fd) == (24, 80)
        # resize and verify each change is detected
        for target in [(40, 120), (10, 40), (3, 10)]:
            _setwinsize(fd, *target)
            time.sleep(0.05)
            assert _get_size(fd) == target


def test_termios_flags(repl_script):
    with pty_session(repl_script) as fd:
        os.write(fd, b"TERMIOS\r")
        flags_str = extract_output(read_until_marker(fd, ":END"), "TERMIOS:", ":END")
        flags = dict(pair.split("=") for pair in flags_str.split(","))
        assert all(k in flags for k in ("ECHO", "ICANON", "ISIG", "VMIN"))
