#!/usr/bin/env python
"""
Minimal REPL for PTY integration tests.

This offers code coverage without mocks, but using real tty features of the natural "live" call to
PromptSession() and session.prompt.  prompt_toolkit sees a real terminal through use of shared
pty_accessories module.
"""

from __future__ import annotations

import os
import sys
import termios
import tty

from pty_accessories import init_subproc_coverage

from prompt_toolkit import PromptSession
from prompt_toolkit.input import create_input
from prompt_toolkit.output import create_output


def main() -> None:
    """Run REPL: SIZE/TERMIOS/QUIT commands, else echo with OUTPUT:...:END."""
    # Signal readiness before creating session (avoids race with PTY setup)
    os.write(sys.stdout.fileno(), b"READY\n")

    # Use natural stdin/stdout - a PTY is indistinguishable from real tty a pty provides the same
    # facility as a real terminal "emulator", allowing us to write tests (and coverage)
    # for natural "live" calls of PromptSession().
    session = PromptSession(input=create_input(), output=create_output())

    try:
        while True:
            result = session.prompt("> ")
            cmd = result.strip().upper()

            if cmd == "SIZE":
                size = os.get_terminal_size(sys.stdin.fileno())
                os.write(
                    sys.stdout.fileno(),
                    f"SIZE:{size.lines}x{size.columns}:END\n".encode(),
                )
            elif cmd == "TERMIOS":
                attrs = termios.tcgetattr(sys.stdin.fileno())
                lflag, iflag = attrs[tty.LFLAG], attrs[tty.IFLAG]
                flags = {
                    "ECHO": bool(lflag & termios.ECHO),
                    "ICANON": bool(lflag & termios.ICANON),
                    "ISIG": bool(lflag & termios.ISIG),
                    "IEXTEN": bool(lflag & termios.IEXTEN),
                    "ICRNL": bool(iflag & termios.ICRNL),
                    "IXON": bool(iflag & termios.IXON),
                    "VMIN": attrs[tty.CC][termios.VMIN],
                }
                flag_str = ",".join(f"{k}={v}" for k, v in sorted(flags.items()))
                os.write(sys.stdout.fileno(), f"TERMIOS:{flag_str}:END\n".encode())
            elif cmd in ("QUIT", "EXIT"):
                break
            else:
                os.write(sys.stdout.fileno(), f"OUTPUT:{result}:END\n".encode())
                break  # Single-shot mode for grapheme tests
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    cov = init_subproc_coverage("pty_repl")
    try:
        main()
    finally:
        if cov is not None:
            cov.stop()
            cov.save()
