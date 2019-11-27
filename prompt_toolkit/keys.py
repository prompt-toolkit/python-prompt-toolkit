from enum import Enum
from typing import Dict, List, NewType, cast

__all__ = [
    'Keys',
    'ALL_KEYS',
    'register_new_key'
    'ParsedKey',
    'parse_key',
]

# Type for keys that are validated.
# (We use this because keys are defined as strings, like 'c-c', but we still
# want mypy to check that we're not passing random strings to places where a
# key is expected.)
ParsedKey = NewType('ParsedKey', str)


# List of the names of the keys that are currently known, and can be used in
# key bindings. This is mostly used as a tool for validating the key bindings.
ALL_KEYS: List[ParsedKey] = []


class _KeysMeta(type):
    """
    Metaclass for `Keys`, which will register all known keys into the
    `ALL_KEYS` list.
    """
    def __new__(cls, name: str, bases, attrs: dict) -> "_KeysMeta":
        for key in attrs.values():
            cls.register_new_key(key)

        return cast("_KeysMeta", super().__new__(cls, name, bases, attrs))

    @classmethod
    def register_new_key(cls, key: str) -> None:
        """
        Register a new key in `ALL_KEYS`.
        """
        if len(key) <= 1:
            raise ValueError(
                'Keys should have a length of at least 2 in order to distinguish '
                'them from individual characters typed on the input.')

        # Add to the `ALL_KEYS` list, so that prompt_toolkit will accept this key
        # in key bindings.
        ALL_KEYS.append(ParsedKey(key))

    def __setattr__(self, name: str, value: str) -> None:
        """
        Allow the definition of new keys by using the following syntax::

            Keys.ControlF5 = "<control-f5>"

        This will automatically register the key in `ALL_KEYS`.
        """
        self.register_new_key(value)
        type.__setattr__(self, name, value)


class Keys(metaclass=_KeysMeta):
    """
    List of keys for use in key bindings.

    Note: Use of this class is completely optional in the key bindings. We can
          as well use string literals anywhere, and this is also what's done
          most of the time in the prompt_toolkit built-in key bindings.

          This class however remains an overview of what key bindings are
          supported. But also, many people like to use the `Keys.SomeKey`
          notation, because editors can provide code completion for that
          notation.

    None 2: In an earlier version, this class was a "StrEnum". This didn't work
          well, because it's impossible to add new values to an enum. We need
          this though, because some users can define custom keys (with custom
          VT100 escape sequences) that are normally not available.
    """
    Escape = 'escape'  # Also Control-[

    ControlAt = 'c-@'  # Also Control-Space.

    ControlA = 'c-a'
    ControlB = 'c-b'
    ControlC = 'c-c'
    ControlD = 'c-d'
    ControlE = 'c-e'
    ControlF = 'c-f'
    ControlG = 'c-g'
    ControlH = 'c-h'
    ControlI = 'c-i'  # Tab
    ControlJ = 'c-j'  # Newline
    ControlK = 'c-k'
    ControlL = 'c-l'
    ControlM = 'c-m'  # Carriage return
    ControlN = 'c-n'
    ControlO = 'c-o'
    ControlP = 'c-p'
    ControlQ = 'c-q'
    ControlR = 'c-r'
    ControlS = 'c-s'
    ControlT = 'c-t'
    ControlU = 'c-u'
    ControlV = 'c-v'
    ControlW = 'c-w'
    ControlX = 'c-x'
    ControlY = 'c-y'
    ControlZ = 'c-z'

    ControlBackslash   = 'c-\\'
    ControlSquareClose = 'c-]'
    ControlCircumflex  = 'c-^'
    ControlUnderscore  = 'c-_'

    ControlLeft        = 'c-left'
    ControlRight       = 'c-right'
    ControlUp          = 'c-up'
    ControlDown        = 'c-down'
    ControlHome        = 'c-home'
    ControlEnd         = 'c-end'
    ControlInsert      = 'c-insert'

    ShiftControlLeft   = 's-c-left'
    ShiftControlRight  = 's-c-right'
    ShiftControlHome   = 's-c-home'
    ShiftControlEnd    = 's-c-end'

    Up          = 'up'
    Down        = 'down'
    Right       = 'right'
    Left        = 'left'

    ShiftLeft   = 's-left'
    ShiftUp     = 's-up'
    ShiftDown   = 's-down'
    ShiftRight  = 's-right'
    ShiftDelete = 's-delete'
    BackTab     = 's-tab'  # shift + tab
    ShiftHome   = 's-home'
    ShiftEnd    = 's-end'
    ShiftInsert = 's-insert'

    Home        = 'home'
    End         = 'end'
    Delete      = 'delete'
    ControlDelete = 'c-delete'
    PageUp      = 'pageup'
    PageDown    = 'pagedown'
    Insert      = 'insert'

    F1 = 'f1'
    F2 = 'f2'
    F3 = 'f3'
    F4 = 'f4'
    F5 = 'f5'
    F6 = 'f6'
    F7 = 'f7'
    F8 = 'f8'
    F9 = 'f9'
    F10 = 'f10'
    F11 = 'f11'
    F12 = 'f12'
    F13 = 'f13'
    F14 = 'f14'
    F15 = 'f15'
    F16 = 'f16'
    F17 = 'f17'
    F18 = 'f18'
    F19 = 'f19'
    F20 = 'f20'
    F21 = 'f21'
    F22 = 'f22'
    F23 = 'f23'
    F24 = 'f24'

    # Matches any key.
    Any = '<any>'

    # Special.
    ScrollUp    = '<scroll-up>'
    ScrollDown  = '<scroll-down>'

    CPRResponse = '<cursor-position-response>'
    Vt100MouseEvent = '<vt100-mouse-event>'
    WindowsMouseEvent = '<windows-mouse-event>'
    BracketedPaste = '<bracketed-paste>'

    # For internal use: key which is ignored.
    # (The key binding for this key should not do anything.)
    Ignore = '<ignore>'

    # Some 'Key' aliases (for backwards-compatibility).
    ControlSpace = ControlAt
    Tab          = ControlI
    Enter        = ControlM
    Backspace    = ControlH


# Aliases.
KEY_ALIASES: Dict[str, str] = {
    'backspace': 'c-h',
    'c-space': 'c-@',
    'enter': 'c-m',
    'tab': 'c-i',
}


def parse_key(key: str) -> ParsedKey:
    """
    Replace key by alias and verify whether it's a valid one.
    """
    # Lookup aliases.
    key = KEY_ALIASES.get(key, key)

    # Replace 'space' by ' '
    if key == 'space':
        key = ' '

    # Accept the key when it's a special key.
    if key in ALL_KEYS:
        return ParsedKey(key)

    # Otherwise, expect a single character.
    if len(key) != 1:
        raise ValueError('Invalid key: %s' % (key, ))

    return ParsedKey(key)


def register_new_key(name: str) -> None:
    """
    Register a new key, e.g. "control-shift-f5", so that this can be used in a
    key binding. (We have some validation in the key bindings that prevent the
    creation of key bindings with unknown keys.)
    """
    Keys.register_new_key(name)
