"""
Interface for an output.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from six import with_metaclass
from prompt_toolkit.layout.screen import Size

__all__ = (
    'Output',
)


class Output(with_metaclass(ABCMeta, object)):
    """
    Base class defining the output interface for a
    :class:`~prompt_toolkit.renderer.Renderer`.

    Actual implementations are
    :class:`~prompt_toolkit.terminal.vt100_output.Vt100_Output` and
    :class:`~prompt_toolkit.terminal.win32_output.Win32Output`.
    """
    @abstractmethod
    def fileno(self):
        " Return the file descriptor to which we can write for the output. "

    @abstractmethod
    def encoding(self):
        """
        Return the encoding for this output, e.g. 'utf-8'.
        (This is used mainly to know which characters are supported by the
        output the data, so that the UI can provide alternatives, when
        required.)
        """

    @abstractmethod
    def write(self, data):
        " Write text (Terminal escape sequences will be removed/escaped.) "

    @abstractmethod
    def write_raw(self, data):
        " Write text. "

    @abstractmethod
    def set_title(self, title):
        " Set terminal title. "

    @abstractmethod
    def clear_title(self):
        " Clear title again. (or restore previous title.) "

    @abstractmethod
    def flush(self):
        " Write to output stream and flush. "

    @abstractmethod
    def erase_screen(self):
        """
        Erases the screen with the background colour and moves the cursor to
        home.
        """

    @abstractmethod
    def enter_alternate_screen(self):
        " Go to the alternate screen buffer. (For full screen applications). "

    @abstractmethod
    def quit_alternate_screen(self):
        " Leave the alternate screen buffer. "

    @abstractmethod
    def enable_mouse_support(self):
        " Enable mouse. "

    @abstractmethod
    def disable_mouse_support(self):
        " Disable mouse. "

    @abstractmethod
    def erase_end_of_line(self):
        """
        Erases from the current cursor position to the end of the current line.
        """

    @abstractmethod
    def erase_down(self):
        """
        Erases the screen from the current line down to the bottom of the
        screen.
        """

    @abstractmethod
    def reset_attributes(self):
        " Reset color and styling attributes. "

    @abstractmethod
    def set_attributes(self, attrs):
        " Set new color and styling attributes. "

    @abstractmethod
    def disable_autowrap(self):
        " Disable auto line wrapping. "

    @abstractmethod
    def enable_autowrap(self):
        " Enable auto line wrapping. "

    @abstractmethod
    def cursor_goto(self, row=0, column=0):
        " Move cursor position. "

    @abstractmethod
    def cursor_up(self, amount):
        " Move cursor `amount` place up. "

    @abstractmethod
    def cursor_down(self, amount):
        " Move cursor `amount` place down. "

    @abstractmethod
    def cursor_forward(self, amount):
        " Move cursor `amount` place forward. "

    @abstractmethod
    def cursor_backward(self, amount):
        " Move cursor `amount` place backward. "

    @abstractmethod
    def hide_cursor(self):
        " Hide cursor. "

    @abstractmethod
    def show_cursor(self):
        " Show cursor. "

    def ask_for_cpr(self):
        """
        Asks for a cursor position report (CPR).
        (VT100 only.)
        """

    def bell(self):
        " Sound bell. "

    def enable_bracketed_paste(self):
        " For vt100 only. "

    def disable_bracketed_paste(self):
        " For vt100 only. "

class StandardOutput(Output):

    def __init__(self, stdout, write_binary=True):

        assert all(hasattr(stdout, a) for a in ('write', 'flush'))

        if write_binary:
            assert hasattr(stdout, 'encoding')

        self._buffer = []
        self.stdout = stdout
        self.write_binary = write_binary

    def fileno(self):
        return self.stdout.fileno()

    def encoding(self):
        return self.stdout.encoding

    def write(self, data):
        self._buffer.append(data)

    def write_raw(self, data):
        " Write text. "
        self._buffer.append(data)

    def flush(self):
        " Write to output stream and flush. "

        if not self._buffer:
            return

        data = ''.join(self._buffer)

        try:
            # (We try to encode ourself, because that way we can replace
            # characters that don't exist in the character set, avoiding
            # UnicodeEncodeError crashes. E.g. u'\xb7' does not appear in 'ascii'.)
            # My Arch Linux installation of july 2015 reported 'ANSI_X3.4-1968'
            # for sys.stdout.encoding in xterm.
            if self.write_binary:
                if hasattr(self.stdout, 'buffer'):
                    out = self.stdout.buffer  # Py3.
                else:
                    out = self.stdout

                out.write(data.encode(self.stdout.encoding or 'utf-8', 'replace'))
            else:
                self.stdout.write(data)

            self.stdout.flush()
        except IOError as e:
            if e.args and e.args[0] == errno.EINTR:
                # Interrupted system call. Can happpen in case of a window
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

        self._buffer = []

    def set_title(self, title): pass
    def clear_title(self): pass
    def erase_screen(self): pass
    def enter_alternate_screen(self): pass
    def quit_alternate_screen(self): pass
    def enable_mouse_support(self): pass
    def disable_mouse_support(self): pass
    def erase_end_of_line(self): pass
    def erase_down(self): pass
    def reset_attributes(self): pass
    def set_attributes(self, attrs): pass
    def disable_autowrap(self): pass
    def enable_autowrap(self): pass
    def cursor_goto(self, row=0, column=0): pass
    def cursor_up(self, amount): pass
    def cursor_down(self, amount): pass
    def cursor_forward(self, amount): pass
    def cursor_backward(self, amount): pass
    def hide_cursor(self): pass
    def show_cursor(self): pass
    def ask_for_cpr(self): pass
    def bell(self): pass
    def enable_bracketed_paste(self): pass
    def disable_bracketed_paste(self): pass

    def get_size(self):
        """
        This seems not needed intuitively (must an output file have a size? 
        can't we avoid it?)
        """

        return Size(rows=40, columns=80)


class DummyOutput(Output):
    """
    For testing. An output class that doesn't render anything.
    """
    def fileno(self):
        " There is no sensible default for fileno(). "
        raise NotImplementedError

    def encoding(self):
        return 'utf-8'

    def write(self, data): pass
    def write_raw(self, data): pass
    def set_title(self, title): pass
    def clear_title(self): pass
    def flush(self): pass
    def erase_screen(self): pass
    def enter_alternate_screen(self): pass
    def quit_alternate_screen(self): pass
    def enable_mouse_support(self): pass
    def disable_mouse_support(self): pass
    def erase_end_of_line(self): pass
    def erase_down(self): pass
    def reset_attributes(self): pass
    def set_attributes(self, attrs): pass
    def disable_autowrap(self): pass
    def enable_autowrap(self): pass
    def cursor_goto(self, row=0, column=0): pass
    def cursor_up(self, amount): pass
    def cursor_down(self, amount): pass
    def cursor_forward(self, amount): pass
    def cursor_backward(self, amount): pass
    def hide_cursor(self): pass
    def show_cursor(self): pass
    def ask_for_cpr(self): pass
    def bell(self): pass
    def enable_bracketed_paste(self): pass
    def disable_bracketed_paste(self): pass

    def get_size(self):
        return Size(rows=40, columns=80)
