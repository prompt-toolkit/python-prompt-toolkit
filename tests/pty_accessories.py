"""PTY testing utilities, ported from 'blessed' by Jeff Quast."""

from __future__ import annotations

import codecs
import contextlib
import os
import platform
import signal
import struct
import sys
import time
import warnings

IS_WINDOWS = platform.system() == "Windows"


def init_subproc_coverage(run_note: str | None = None):
    """
    Initialize coverage tracking in a forked subprocess.

    Ported from blessed library's test accessories. Call this at the start
    of any script executed via PTY fork/exec to enable coverage tracking.

    :param run_note: Optional note for coverage context (unused).
    :returns: Coverage instance or None if coverage not available.
    """
    try:
        import coverage
    except ImportError:
        return None

    # Look for pyproject.toml or tox.ini as coverage config
    test_dir = os.path.dirname(__file__)
    for config_name in ("pyproject.toml", "tox.ini"):
        config_path = os.path.join(test_dir, os.pardir, config_name)
        if os.path.exists(config_path):
            break
    else:
        config_path = None

    cov = coverage.Coverage(config_file=config_path)
    cov.start()
    return cov


if not IS_WINDOWS:
    import fcntl
    import pty
    import termios

# note how the tty driver translates '\n' output to '\r\n'
SEND_SEMAPHORE = b"SEMAPHORE\n"
RECV_SEMAPHORE = b"SEMAPHORE\r\n"


def _setwinsize(fd: int, rows: int, cols: int) -> None:
    """Set PTY window size via TIOCSWINSZ ioctl."""
    TIOCSWINSZ = getattr(termios, "TIOCSWINSZ", -2146929561)
    fcntl.ioctl(fd, TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def read_until_marker(fd: int, marker: str, timeout: float = 5.0) -> str:
    """Read from fd until marker found or timeout."""
    decoder = codecs.getincrementaldecoder("utf8")()
    output = ""
    start = time.time()
    while marker not in output:
        if time.time() - start > timeout:
            raise TimeoutError(f"Marker {marker!r} not found. Got: {output!r}")
        try:
            chunk = os.read(fd, 1)
        except OSError:
            break
        if not chunk:
            break
        output += decoder.decode(chunk, final=False)
    return output


@contextlib.contextmanager
def echo_off(fd: int):
    """Disable PTY echo."""
    attrs = termios.tcgetattr(fd)
    try:
        attrs[3] = attrs[3] & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        yield
    finally:
        attrs[3] = attrs[3] | termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, attrs)


def spawn_pty_process(script: str, rows: int = 24, cols: int = 80) -> tuple[int, int]:
    """Spawn script in PTY with given size. Returns (master_fd, pid)."""
    with warnings.catch_warnings():
        # modern python 3.14+ raises a DeprecationWarning, I guess they may plan to delete pty
        # module someday and we will have to manage our own backport?
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        pid, master_fd = pty.fork()
    if pid == 0:
        # note how sys.executable is used, to ensure the given script is executed with exactly the
        # same python interpreter as used for the parent process, receiving all of its environment
        # variables, site-packages, PATH and PYTHONPATH that got it here.
        os.execv(sys.executable, [sys.executable, script])
    attrs = termios.tcgetattr(master_fd)
    attrs[3] = attrs[3] & ~termios.ECHO
    termios.tcsetattr(master_fd, termios.TCSANOW, attrs)
    _setwinsize(master_fd, rows, cols)
    return master_fd, pid


def cleanup_child(pid: int, master_fd: int, timeout: float = 5.0) -> int:
    """Wait for child, kill if needed. Returns exit status."""
    start = time.time()
    while True:
        result, status = os.waitpid(pid, os.WNOHANG)
        if result != 0:
            # if the child is not ready to exit, send EOF, causes most programs to exit.
            os.close(master_fd)
            return os.WEXITSTATUS(status)
        if time.time() - start > timeout:
            # but after timeout, we have a "locked up" client, "not responding", most likely we made
            # an error in our "call, reply" pattern of the tests.  Kill the program so that the
            # MainProcess can become unblocked reading their side of the pty and move on.
            try:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except OSError:
                pass
            os.close(master_fd)
            raise TimeoutError(f"Child {pid} did not exit within {timeout}s")
        time.sleep(0.05)


def extract_output(text: str, start: str = "OUTPUT:", end: str = ":END") -> str:
    """Extract text between markers."""
    if start not in text:
        return ""
    after = text.split(start, 1)[1]
    return after.split(end, 1)[0] if end in after else after


@contextlib.contextmanager
def pty_session(script: str, rows: int = 24, cols: int = 80):
    """
    Context manager for PTY test sessions.

    Spawns pty_repl.py, waits for READY, yields master_fd, then sends QUIT
    and cleans up the child process.

    Usage::

        with pty_session(repl_script, rows=24, cols=80) as fd:
            os.write(fd, b"some input\\r")
            output = read_until_marker(fd, ":END")
    """
    master_fd, pid = spawn_pty_process(script, rows, cols)
    try:
        read_until_marker(master_fd, "READY")
        yield master_fd
    finally:
        os.write(master_fd, b"QUIT\r")
        time.sleep(0.1)
        cleanup_child(pid, master_fd)
