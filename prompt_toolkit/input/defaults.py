import sys
from typing import Optional, TextIO

from prompt_toolkit.utils import is_windows

from .base import Input

__all__ = [
    "create_input",
    "create_pipe_input",
]


def create_input(stdin: Optional[TextIO] = None) -> Input:
    """
    Create the appropriate `Input` object for the current os/environment.
    """
    if is_windows():
        from .win32 import Win32Input

        return Win32Input(stdin or sys.stdin)
    else:
        from .vt100 import Vt100Input

        # If no input TextIO is given, use stdin/stdout.
        if stdin is None:
            # Try stdin first, if it's a TTY.
            if sys.stdin.isatty():
                stdin = sys.stdin
            # If stdin is not a TTY, it's possible we're piping something into
            # stdin. Use stdout instead if stdout is a TTY. (We can actually
            # use stdout to read input from, this is how a $PAGER works.)
            elif sys.stdout.isatty():
                stdin = sys.stdout
            # If stdout is also not a tty, then use stdin. (This will print a
            # "Input is not a terminal" warning in `Vt100Input`.)
            else:
                stdin = sys.stdin

        return Vt100Input(stdin)


def create_pipe_input() -> Input:
    """
    Create an input pipe.
    This is mostly useful for unit testing.
    """
    if is_windows():
        from .win32_pipe import Win32PipeInput

        return Win32PipeInput()
    else:
        from .posix_pipe import PosixPipeInput

        return PosixPipeInput()
