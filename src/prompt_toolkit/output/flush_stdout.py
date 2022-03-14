import errno
import os
import sys
from contextlib import contextmanager
from typing import IO, Iterator, TextIO, cast

__all__ = ["flush_stdout"]


def flush_stdout(stdout: TextIO, data: str, write_binary: bool) -> None:
    try:
        # Ensure that `stdout` is made blocking when writing into it.
        # Otherwise, when uvloop is activated (which makes stdout
        # non-blocking), and we write big amounts of text, then we get a
        # `BlockingIOError` here.
        with _blocking_io(stdout):
            # (We try to encode ourself, because that way we can replace
            # characters that don't exist in the character set, avoiding
            # UnicodeEncodeError crashes. E.g. u'\xb7' does not appear in 'ascii'.)
            # My Arch Linux installation of july 2015 reported 'ANSI_X3.4-1968'
            # for sys.stdout.encoding in xterm.
            out: IO[bytes]
            if write_binary:
                if hasattr(stdout, "buffer"):
                    out = stdout.buffer
                else:
                    # IO[bytes] was given to begin with.
                    # (Used in the unit tests, for instance.)
                    out = cast(IO[bytes], stdout)
                out.write(data.encode(stdout.encoding or "utf-8", "replace"))
            else:
                stdout.write(data)

            stdout.flush()
    except OSError as e:
        if e.args and e.args[0] == errno.EINTR:
            # Interrupted system call. Can happen in case of a window
            # resize signal. (Just ignore. The resize handler will render
            # again anyway.)
            pass
        elif e.args and e.args[0] == 0:
            # This can happen when there is a lot of output and the user
            # sends a KeyboardInterrupt by pressing Control-C. E.g. in
            # a Python REPL when we execute "while True: print('test')".
            # (The `ptpython` REPL uses this `Output` class instead of
            # `stdout` directly -- in order to be network transparent.)
            # So, just ignore.
            pass
        else:
            raise


@contextmanager
def _blocking_io(io: IO[str]) -> Iterator[None]:
    """
    Ensure that the FD for `io` is set to blocking in here.
    """
    if sys.platform == "win32":
        # On Windows, the `os` module doesn't have a `get/set_blocking`
        # function.
        yield
        return

    try:
        fd = io.fileno()
        blocking = os.get_blocking(fd)
    except:  # noqa
        # Failed somewhere.
        # `get_blocking` can raise `OSError`.
        # The io object can raise `AttributeError` when no `fileno()` method is
        # present if we're not a real file object.
        blocking = True  # Assume we're good, and don't do anything.

    try:
        # Make blocking if we weren't blocking yet.
        if not blocking:
            os.set_blocking(fd, True)

        yield

    finally:
        # Restore original blocking mode.
        if not blocking:
            os.set_blocking(fd, blocking)
