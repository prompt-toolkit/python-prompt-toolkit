"""
Parser for VT100 input stream.
"""
from __future__ import unicode_literals

import os
import re
import six
import termios
import tty

from ..keys import Keys
from ..key_binding.input_processor import KeyPress

__all__ = (
    'InputStream',
    'raw_mode',
    'cooked_mode',
)

_DEBUG_RENDERER_INPUT = False
_DEBUG_RENDERER_INPUT_FILENAME = 'prompt-toolkit-render-input.log'


# Regex matching any CPR response
# (Note that we use '\Z' instead of '$', because '$' could include a trailing
# newline.)
_cpr_response_re = re.compile('^' + re.escape('\x1b[') + r'\d+;\d+R\Z')

# Regex matching any valid prefix of a CPR response.
# (Note that it doesn't contain the last character, the 'R'. The prefix has to
# be shorter.)
_cpr_response_prefix_re = re.compile('^' + re.escape('\x1b[') + r'[\d;]*\Z')


class _Flush(object):
    """ Helper object to indicate flush operation to the parser. """
    pass


class InputStream(object):
    """
    Parser for VT100 input stream.

    Feed the data through the `feed` method and the correct callbacks of the
    `input_processor` will be called.

    ::

        h = InputStreamHandler()
        i = InputStream(h)
        i.feed('data\x01...')

    :attr input_processor: :class:`~prompt_toolkit.key_binding.InputProcessor` instance.
    """
    # Lookup table of ANSI escape sequences for a VT100 terminal
    mappings = {
        '\x1b': Keys.Escape,

        '\x00': Keys.ControlSpace,  # Control-Space (Also for Ctrl-@)
        '\x01': Keys.ControlA,  # Control-A (home)
        '\x02': Keys.ControlB,  # Control-B (emacs cursor left)
        '\x03': Keys.ControlC,  # Control-C (interrupt)
        '\x04': Keys.ControlD,  # Control-D (exit)
        '\x05': Keys.ControlE,  # Contrel-E (end)
        '\x06': Keys.ControlF,  # Control-F (cursor forward)
        '\x07': Keys.ControlG,  # Control-G
        '\x08': Keys.ControlH,  # Control-H (8) (Identical to '\b')
        '\x09': Keys.ControlI,  # Control-I (9) (Identical to '\t')
        '\x0a': Keys.ControlJ,  # Control-J (10) (Identical to '\n')
        '\x0b': Keys.ControlK,  # Control-K (delete until end of line; vertical tab)
        '\x0c': Keys.ControlL,  # Control-L (clear; form feed)
        '\x0d': Keys.ControlM,  # Control-M (13) (Identical to '\r')
        '\x0e': Keys.ControlN,  # Control-N (14) (history forward)
        '\x0f': Keys.ControlO,  # Control-O (15)
        '\x10': Keys.ControlP,  # Control-P (16) (history back)
        '\x11': Keys.ControlQ,  # Control-Q
        '\x12': Keys.ControlR,  # Control-R (18) (reverse search)
        '\x13': Keys.ControlS,  # Control-S (19) (forward search)
        '\x14': Keys.ControlT,  # Control-T
        '\x15': Keys.ControlU,  # Control-U
        '\x16': Keys.ControlV,  # Control-V
        '\x17': Keys.ControlW,  # Control-W
        '\x18': Keys.ControlX,  # Control-X
        '\x19': Keys.ControlY,  # Control-Y (25)
        '\x1a': Keys.ControlZ,  # Control-Z

        '\x1c': Keys.ControlBackslash,  # Both Control-\ and Ctrl-|
        '\x1d': Keys.ControlSquareClose,  # Control-]
        '\x1e': Keys.ControlCircumflex,  # Control-^
        '\x1f': Keys.ControlUnderscore,  # Control-underscore (Also for Ctrl-hypen.)
        '\x7f': Keys.Backspace,  # (127) Backspace
        '\x1b[A': Keys.Up,
        '\x1b[B': Keys.Down,
        '\x1b[C': Keys.Right,
        '\x1b[D': Keys.Left,
        '\x1b[H': Keys.Home,
        '\x1bOH': Keys.Home,
        '\x1b[F': Keys.End,
        '\x1bOF': Keys.End,
        '\x1b[3~': Keys.Delete,
        '\x1b[3;2~': Keys.ShiftDelete,  # xterm, gnome-terminal.
        '\x1b[1~': Keys.Home,  # tmux
        '\x1b[4~': Keys.End,  # tmux
        '\x1b[5~': Keys.PageUp,
        '\x1b[6~': Keys.PageDown,
        '\x1b[7~': Keys.Home,  # xrvt
        '\x1b[8~': Keys.End,  # xrvt
        '\x1b[Z': Keys.BackTab,  # shift + tab

        '\x1bOP': Keys.F1,
        '\x1bOQ': Keys.F2,
        '\x1bOR': Keys.F3,
        '\x1bOS': Keys.F4,
        '\x1b[11~': Keys.F1,  # rxvt-unicode
        '\x1b[12~': Keys.F2,  # rxvt-unicode
        '\x1b[13~': Keys.F3,  # rxvt-unicode
        '\x1b[14~': Keys.F4,  # rxvt-unicode
        '\x1b[15~': Keys.F5,
        '\x1b[17~': Keys.F6,
        '\x1b[18~': Keys.F7,
        '\x1b[19~': Keys.F8,
        '\x1b[20~': Keys.F9,
        '\x1b[21~': Keys.F10,
        '\x1b[23~': Keys.F11,
        '\x1b[24~': Keys.F12,
        '\x1b[25~': Keys.F13,
        '\x1b[26~': Keys.F14,
        '\x1b[28~': Keys.F15,
        '\x1b[29~': Keys.F16,
        '\x1b[31~': Keys.F17,
        '\x1b[32~': Keys.F18,
        '\x1b[33~': Keys.F19,
        '\x1b[34~': Keys.F20,
        '\x1b[1;5D': Keys.ControlLeft,   # Cursor Mode
        '\x1b[1;5C': Keys.ControlRight,  # Cursor Mode
        '\x1b[1;5A': Keys.ControlUp,     # Cursor Mode
        '\x1b[1;5B': Keys.ControlDown,   # Cursor Mode
        '\x1bOD': Keys.ControlLeft,     # Application Mode (tmux)
        '\x1bOC': Keys.ControlRight,    # Application Mode (tmux)
        '\x1bOA': Keys.ControlUp,       # Application Mode (tmux)
        '\x1bOB': Keys.ControlDown,     # Application Mode (tmux)

        # Meta + arrow keys. Several terminals handle this differently.
        # The following sequences are for xterm and gnome-terminal.
        #     (Iterm sends ESC followed by the normal arrow_up/down/left/right
        #     sequences, and the OSX Terminal sends ESCb and ESCf for "alt
        #     arrow_left" and "alt arrow_right." We don't handle these
        #     explicitely, in here, because would could not distinguesh between
        #     pressing ESC (to go to Vi navigation mode), followed by just the
        #     'b' or 'f' key. These combinations are handled in
        #     the input processor.)
        '\x1b[1;3D': (Keys.Escape, Keys.Left),
        '\x1b[1;3C': (Keys.Escape, Keys.Right),
        '\x1b[1;3A': (Keys.Escape, Keys.Up),
        '\x1b[1;3B': (Keys.Escape, Keys.Down),
    }

    def __init__(self, input_processor):
        self._input_processor = input_processor
        self.reset()

        if _DEBUG_RENDERER_INPUT:
            self.LOG = open(_DEBUG_RENDERER_INPUT_FILENAME, 'ab')

    def reset(self, request=False):
        self._start_parser()

    def _start_parser(self):
        """
        Start the parser coroutine.
        """
        self._input_parser = self._input_parser_generator()
        self._input_parser.send(None)

    def _get_matches(self, prefix):
        """
        Return the keys that map to this prefix.
        """
        # (hard coded) If we match a CPR response, return Keys.CPRResponse.
        # (This one doesn't fit in the mappings, because it contains
        # integer variables.)
        if _cpr_response_re.match(prefix):
            return [Keys.CPRResponse]

        # Otherwise, use the mappings.
        return [v for k, v in self.mappings.items() if k == prefix]

    def _is_prefix_of_longer_match(self, prefix):
        """
        True when there is any key that start with this characters.
        """
        # (hard coded) If this could be a prefix of a CPR response, return
        # True.
        if _cpr_response_prefix_re.match(prefix):
            return True

        # If this could be a prefix of anything else, also return True.
        return any(v for k, v in self.mappings.items() if k.startswith(prefix) and k != prefix)

    def _input_parser_generator(self):
        """
        Coroutine (state machine) for the input parser.
        """
        prefix = ''
        retry = False
        flush = False

        while True:
            flush = False

            if retry:
                retry = False
            else:
                # Get next character.
                c = yield

                if c == _Flush:
                    flush = True
                else:
                    prefix += c

            # If we have some data, check for matches.
            if prefix:
                is_prefix_of_longer_match = self._is_prefix_of_longer_match(prefix)
                matches = self._get_matches(prefix)

                # Exact matches found, call handlers..
                if (flush or not is_prefix_of_longer_match) and matches:
                    self._call_handler(matches[0], prefix)
                    prefix = ''

                # No exact matches found.
                elif (flush or not is_prefix_of_longer_match) and not matches:
                    found = False
                    retry = True

                    # Loop over the input, try the longest match first and
                    # shift.
                    for i in range(len(prefix), 0, -1):
                        matches = self._get_matches(prefix[:i])
                        if matches:
                            self._call_handler(matches[0], prefix[:i])
                            prefix = prefix[i:]
                            found = True

                    if not found:
                        self._call_handler(prefix[0], prefix[0])
                        prefix = prefix[1:]

    def _call_handler(self, key, insert_text):
        """
        Callback to handler.
        """
        if isinstance(key, tuple):
            for k in key:
                self._call_handler(k, insert_text)
        else:
            self._input_processor.feed_key(KeyPress(key, insert_text))

    def feed(self, data):
        """
        Feed the input stream.
        """
        assert isinstance(data, six.text_type)

        if _DEBUG_RENDERER_INPUT:
            self.LOG.write(repr(data).encode('utf-8') + b'\n')
            self.LOG.flush()

        for c in data:
            self._input_parser.send(c)

    def flush(self):
        """
        Flush the buffer of the input stream.

        This will allow us to handle the escape key (or maybe meta) sooner.
        The input received by the escape key is actually the same as the first
        characters of e.g. Arrow-Up, so without knowing what follows the escape
        sequence, we don't know whether escape has been pressed, or whether
        it's something else. This flush function should be called after a
        timeout, and processes everything that's still in the buffer as-is, so
        without assuming any characters will folow.
        """
        self._input_parser.send(_Flush)

    def feed_and_flush(self, data):
        """
        Wrapper around ``feed`` and ``flush``.
        """
        self.feed(data)
        self.flush()


class raw_mode(object):
    """
    ::

        with raw_mode(stdin):
            ''' the pseudo-terminal stdin is now used in raw mode '''
    """
    def __init__(self, fileno):
        self.fileno = fileno
        self.attrs_before = termios.tcgetattr(fileno)

    def __enter__(self):
        # NOTE: On os X systems, using pty.setraw() fails. Therefor we are using this:
        newattr = termios.tcgetattr(self.fileno)
        newattr[tty.LFLAG] = self._patch(newattr[tty.LFLAG])
        termios.tcsetattr(self.fileno, termios.TCSANOW, newattr)

        # Put the terminal in cursor mode. (Instead of application mode.)
        os.write(self.fileno, b'\x1b[?1l')

    def _patch(self, attrs):
        return attrs & ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)

    def __exit__(self, *a, **kw):
        termios.tcsetattr(self.fileno, termios.TCSANOW, self.attrs_before)

        # # Put the terminal in application mode.
        # self._stdout.write('\x1b[?1h')


class cooked_mode(raw_mode):
    """
    (The opposide of ``raw_mode``::

        with cooked_mode(stdin):
            ''' the pseudo-terminal stdin is now used in cooked mode. '''
    """
    def _patch(self, attrs):
        return attrs | (termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)
