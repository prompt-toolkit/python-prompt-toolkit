from __future__ import unicode_literals

from ..utils import DummyContext
from .base import Input
from .posix_utils import PosixStdinReader
from .vt100_parser import Vt100Parser
import io
import os
import sys
import termios
import tty

__all__ = (
    'Vt100Input',
    'PipeInput',
    'raw_mode',
    'cooked_mode',
)


class Vt100Input(Input):
    def __init__(self, stdin):
        # The input object should be a TTY.
        assert stdin.isatty()

        # Test whether the given input object has a file descriptor.
        # (Idle reports stdin to be a TTY, but fileno() is not implemented.)
        try:
            # This should not raise, but can return 0.
            stdin.fileno()
        except io.UnsupportedOperation:
            if 'idlelib.run' in sys.modules:
                raise io.UnsupportedOperation(
                    'Stdin is not a terminal. Running from Idle is not supported.')
            else:
                raise io.UnsupportedOperation('Stdin is not a terminal.')

        self.stdin = stdin

        self._buffer = []  # Buffer to collect the Key objects.
        self.stdin_reader = PosixStdinReader(stdin.fileno())
        self.vt100_parser = Vt100Parser(
            lambda key: self._buffer.append(key))

    def read_keys(self):
        " Read list of KeyPress. "
        # Read text from stdin.
        data = self.stdin_reader.read()

        # Pass it through our vt100 parser.
        self.vt100_parser.feed(data)

        # Return result.
        result = self._buffer
        self._buffer = []
        return result

    def flush(self):
        # Flush all pending keys. (This is most important to flush the vt100
        # 'Escape' key early when nothing else follows.)
        self.vt100_parser.flush()

    @property
    def closed(self):
        return self.stdin_reader.closed

    def raw_mode(self):
        return raw_mode(self.stdin.fileno())

    def cooked_mode(self):
        return cooked_mode(self.stdin.fileno())

    def fileno(self):
        return self.stdin.fileno()


class PipeInput(Vt100Input):
    """
    Input that is send through a pipe.
    This is useful if we want to send the input programatically into the
    interface. Mostly useful for unit testing.

    Usage::

        input = PipeInput()
        input.send('inputdata')
    """
    def __init__(self, text=''):
        self._r, self._w = os.pipe()


        class Stdin(object):
            def isatty(stdin):
                return True

            def fileno(stdin):
                return self._r

        super(PipeInput, self).__init__(Stdin())
        self.send_text(text)

    def send_text(self, data):
        " Send text to the input. "
        os.write(self._w, data.encode('utf-8'))

    def raw_mode(self):
        return DummyContext()

    def cooked_mode(self):
        return DummyContext()

    def close(self):
        " Close pipe fds. "
        os.close(self._r)
        os.close(self._w)
        self._r = None
        self._w = None


class raw_mode(object):
    """
    ::

        with raw_mode(stdin):
            ''' the pseudo-terminal stdin is now used in raw mode '''

    We ignore errors when executing `tcgetattr` fails.
    """
    # There are several reasons for ignoring errors:
    # 1. To avoid the "Inappropriate ioctl for device" crash if somebody would
    #    execute this code (In a Python REPL, for instance):
    #
    #         import os; f = open(os.devnull); os.dup2(f.fileno(), 0)
    #
    #    The result is that the eventloop will stop correctly, because it has
    #    to logic to quit when stdin is closed. However, we should not fail at
    #    this point. See:
    #      https://github.com/jonathanslenders/python-prompt-toolkit/pull/393
    #      https://github.com/jonathanslenders/python-prompt-toolkit/issues/392

    # 2. Related, when stdin is an SSH pipe, and no full terminal was allocated.
    #    See: https://github.com/jonathanslenders/python-prompt-toolkit/pull/165
    def __init__(self, fileno):
        self.fileno = fileno
        try:
            self.attrs_before = termios.tcgetattr(fileno)
        except termios.error:
            # Ignore attribute errors.
            self.attrs_before = None

    def __enter__(self):
        # NOTE: On os X systems, using pty.setraw() fails. Therefor we are using this:
        try:
            newattr = termios.tcgetattr(self.fileno)
        except termios.error:
            pass
        else:
            newattr[tty.LFLAG] = self._patch_lflag(newattr[tty.LFLAG])
            newattr[tty.IFLAG] = self._patch_iflag(newattr[tty.IFLAG])
            termios.tcsetattr(self.fileno, termios.TCSANOW, newattr)

            # Put the terminal in cursor mode. (Instead of application mode.)
            os.write(self.fileno, b'\x1b[?1l')

    @classmethod
    def _patch_lflag(cls, attrs):
        return attrs & ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)

    @classmethod
    def _patch_iflag(cls, attrs):
        return attrs & ~(
            # Disable XON/XOFF flow control on output and input.
            # (Don't capture Ctrl-S and Ctrl-Q.)
            # Like executing: "stty -ixon."
            termios.IXON | termios.IXOFF |

            # Don't translate carriage return into newline on input.
            termios.ICRNL | termios.INLCR | termios.IGNCR
        )

    def __exit__(self, *a, **kw):
        if self.attrs_before is not None:
            try:
                termios.tcsetattr(self.fileno, termios.TCSANOW, self.attrs_before)
            except termios.error:
                pass

            # # Put the terminal in application mode.
            # self._stdout.write('\x1b[?1h')


class cooked_mode(raw_mode):
    """
    The opposide of ``raw_mode``, used when we need cooked mode inside a
    `raw_mode` block.  Used in `Application.run_in_terminal`.::

        with cooked_mode(stdin):
            ''' the pseudo-terminal stdin is now used in cooked mode. '''
    """
    @classmethod
    def _patch_lflag(cls, attrs):
        return attrs | (termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)

    @classmethod
    def _patch_iflag(cls, attrs):
        # Turn the ICRNL flag back on. (Without this, calling `input()` in
        # run_in_terminal doesn't work and displays ^M instead. Ptpython
        # evaluates commands using `run_in_terminal`, so it's important that
        # they translate ^M back into ^J.)
        return attrs | termios.ICRNL
