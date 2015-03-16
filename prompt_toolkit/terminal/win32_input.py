from ctypes import windll, pointer, c_int
from ctypes.wintypes import DWORD

from prompt_toolkit.key_binding.input_processor import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.win32_types import EventTypes, KEY_EVENT_RECORD, INPUT_RECORD, STD_INPUT_HANDLE

__all__ = (
    'ConsoleInputReader',
    'raw_mode',
    'cooked_mode'
)


class ConsoleInputReader(object):
    # Keys with character data.
    mappings = {
        b'\x1b': Keys.Escape,

        b'\x00': Keys.ControlSpace,  # Control-Space (Also for Ctrl-@)
        b'\x01': Keys.ControlA,  # Control-A (home)
        b'\x02': Keys.ControlB,  # Control-B (emacs cursor left)
        b'\x03': Keys.ControlC,  # Control-C (interrupt)
        b'\x04': Keys.ControlD,  # Control-D (exit)
        b'\x05': Keys.ControlE,  # Contrel-E (end)
        b'\x06': Keys.ControlF,  # Control-F (cursor forward)
        b'\x07': Keys.ControlG,  # Control-G
        b'\x08': Keys.ControlH,  # Control-H (8) (Identical to '\b')
        b'\x09': Keys.ControlI,  # Control-I (9) (Identical to '\t')
        b'\x0a': Keys.ControlJ,  # Control-J (10) (Identical to '\n')
        b'\x0b': Keys.ControlK,  # Control-K (delete until end of line; vertical tab)
        b'\x0c': Keys.ControlL,  # Control-L (clear; form feed)
        b'\x0d': Keys.ControlM,  # Control-M (13) (Identical to '\r')
        b'\x0e': Keys.ControlN,  # Control-N (14) (history forward)
        b'\x0f': Keys.ControlO,  # Control-O (15)
        b'\x10': Keys.ControlP,  # Control-P (16) (history back)
        b'\x11': Keys.ControlQ,  # Control-Q
        b'\x12': Keys.ControlR,  # Control-R (18) (reverse search)
        b'\x13': Keys.ControlS,  # Control-S (19) (forward search)
        b'\x14': Keys.ControlT,  # Control-T
        b'\x15': Keys.ControlU,  # Control-U
        b'\x16': Keys.ControlV,  # Control-V
        b'\x17': Keys.ControlW,  # Control-W
        b'\x18': Keys.ControlX,  # Control-X
        b'\x19': Keys.ControlY,  # Control-Y (25)
        b'\x1a': Keys.ControlZ,  # Control-Z

        b'\x1c': Keys.ControlBackslash,  # Both Control-\ and Ctrl-|
        b'\x1d': Keys.ControlSquareClose,  # Control-]
        b'\x1e': Keys.ControlCircumflex,  # Control-^
        b'\x1f': Keys.ControlUnderscore,  # Control-underscore (Also for Ctrl-hypen.)
        b'\x7f': Keys.Backspace,  # (127) Backspace
    }

    # Keys that don't carry character data.
    keycodes = {
        # Home/End
        33: Keys.PageUp,
        34: Keys.PageDown,
        35: Keys.End,
        36: Keys.Home,

        # Arrows
        37: Keys.Left,
        38: Keys.Up,
        39: Keys.Right,
        40: Keys.Down,

        46: Keys.Delete,

        # F-keys.
        112: Keys.F1,
        113: Keys.F2,
        114: Keys.F3,
        115: Keys.F4,
        116: Keys.F5,
        117: Keys.F6,
        118: Keys.F7,
        119: Keys.F8,
        120: Keys.F9,
        121: Keys.F10,
        122: Keys.F11,
        123: Keys.F12,
    }

    LEFT_ALT_PRESSED = 0x0002
    RIGHT_ALT_PRESSED = 0x0001
    SHIFT_PRESSED = 0x0010
    LEFT_CTRL_PRESSED = 0x0008
    RIGHT_CTRL_PRESSED = 0x0004

    def __init__(self):
        self.handle = windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)

    def read(self):
        """
        Read from the Windows console and return a list of `KeyPress` instances.
        It can return an empty list when there was nothing to read. (This
        function doesn't block.)

        http://msdn.microsoft.com/en-us/library/windows/desktop/ms684961(v=vs.85).aspx
        """
        max_count = 1024  # Read max 1024 events at the same time.
        result = []

        read = c_int(0)

        arrtype = INPUT_RECORD * max_count
        input_records = arrtype()

        # Get next batch of input event.
        windll.kernel32.ReadConsoleInputA(self.handle, pointer(input_records), max_count, pointer(read))

        for i in range(read.value):
            ir = input_records[i]

            ev = getattr(ir.Event, EventTypes[ir.EventType])

            # Process if this is a key event. (We also have mouse, menu and
            # focus events.)
            if type(ev) == KEY_EVENT_RECORD and ev.KeyDown:
                key_presses = self._event_to_key_presses(ev)
                if key_presses:
                    result.extend(key_presses)

        return result

    def _event_to_key_presses(self, ev):
        """
        For this `KEY_EVENT_RECORD`, return a list of `KeyPress` instances.
        """
        assert type(ev) == KEY_EVENT_RECORD and ev.KeyDown

        result = None

        if ev.AsciiChar == b'\0':
            if ev.VirtualKeyCode in self.keycodes:
                result = KeyPress(self.keycodes[ev.VirtualKeyCode], '')
        else:
            if ev.AsciiChar in self.mappings:
                result = KeyPress(self.mappings[ev.AsciiChar], ev.AsciiChar.decode('ascii'))
            else:
                result = KeyPress(ev.AsciiChar.decode('ascii'), ev.AsciiChar.decode('ascii'))

        # Correctly handle Control-Arrow keys.
        if (ev.ControlKeyState & self.LEFT_CTRL_PRESSED or
                ev.ControlKeyState & self.RIGHT_CTRL_PRESSED) and result:
            if result.key == Keys.Left:
                 result.key = Keys.ControlLeft

            if result.key == Keys.Right:
                 result.key = Keys.ControlRight

            if result.key == Keys.Up:
                 result.key = Keys.ControlUp

            if result.key == Keys.Down:
                 result.key = Keys.ControlDown

        # Turn 'Tab' into 'BackTab' when shift was pressed.
        if ev.ControlKeyState & self.SHIFT_PRESSED and result:
            if result.key == Keys.Tab:
                result.key = Keys.BackTab

        # Turn 'Space' into 'ControlSpace' when control was pressed.
        if (ev.ControlKeyState & self.LEFT_CTRL_PRESSED or
                ev.ControlKeyState & self.RIGHT_CTRL_PRESSED) and result and result.data == ' ':
            result = KeyPress(Keys.ControlSpace, ' ')

        # Return result. If alt was pressed, prefix the result with an
        # 'Escape' key, just like unix VT100 terminals do.
        if result:
            meta_pressed = ev.ControlKeyState & self.LEFT_ALT_PRESSED or \
                ev.ControlKeyState & self.RIGHT_ALT_PRESSED

            if meta_pressed:
                return [KeyPress(Keys.Escape, ''), result]
            else:
                return [result]

        else:
            return []


class raw_mode(object):
    """
    ::

        with raw_mode(stdin):
            ''' the windows terminal is now in 'raw' mode. '''

    The ``fileno`` attribute is ignored. This is to be compatble with the
    `raw_input` method of `.vt100_input`.
    """
    def __init__(self, fileno=None):
        self.handle = windll.kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE

    def __enter__(self):
        # Remember original mode.
        original_mode = DWORD()
        windll.kernel32.GetConsoleMode(self.handle, pointer(original_mode))
        self.original_mode = original_mode

        self._patch()

    def _patch(self):
        # Set raw
        ENABLE_ECHO_INPUT = 0x0004
        ENABLE_LINE_INPUT = 0x0002
        ENABLE_PROCESSED_INPUT = 0x0001

        windll.kernel32.SetConsoleMode(
            self.handle, self.original_mode.value &
            ~(ENABLE_ECHO_INPUT | ENABLE_LINE_INPUT | ENABLE_PROCESSED_INPUT))

    def __exit__(self, *a, **kw):
        # Restore original mode
        windll.kernel32.SetConsoleMode(self.handle, self.original_mode)


class cooked_mode(raw_mode):
    """
    ::

        with cooked_mode(stdin):
            ''' the pseudo-terminal stdin is now used in raw mode '''
    """
    def _patch(self):
        # Set cooked.
        ENABLE_ECHO_INPUT = 0x0004
        ENABLE_LINE_INPUT = 0x0002
        ENABLE_PROCESSED_INPUT = 0x0001

        windll.kernel32.SetConsoleMode(
            self.handle, self.original_mode.value |
            (ENABLE_ECHO_INPUT | ENABLE_LINE_INPUT | ENABLE_PROCESSED_INPUT))
