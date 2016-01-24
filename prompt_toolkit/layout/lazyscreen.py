"""
LazyScreen is the screen that a UserControl generates.
"""
from __future__ import unicode_literals
from prompt_toolkit.token import Token

from .screen import Point, Char


class LazyScreen(object):
    """
    User controls generate a :class:`.LazyScreen`.

    :param get_line: Callable that returns the current line. This can be a
        generator that yields (Token, text) tuples.
    :param get_line_count: Callable that returns the number of lines.
    """
    def __init__(self, get_line=None, get_line_count=None,
                 cursor_position=None, menu_position=None, default_char=None):
        assert callable(get_line)
        assert callable(get_line_count)
        assert cursor_position is None or isinstance(cursor_position, Point)
        assert menu_position is None or isinstance(menu_position, Point)
        assert default_char is None or isinstance(default_char, Char)

        self.get_line = get_line  # TODO: Add cache!
        self.get_line_count = get_line_count  # TODO: Add cache!

        self.cursor_position = cursor_position or Point(0, 0)
        self.menu_position = menu_position

        self.default_char = default_char
