"""
LazyScreen is the screen that a UserControl generates.
"""
from __future__ import unicode_literals


class LazyScreen(object):
    """
    User controls generate a :class:`.LazyScreen`.

    :param get_line: Callable that returns the current line. This can be a
        generator that yields (Token, text) tuples.
    :param get_line_count: Callable that returns the number of lines.
    :param line_processors: None or list of `LineProcessor` instances.
    """
    def __init__(self, get_line=None, get_line_count=None, line_processors=None):
        assert callable(get_line)
        assert callable(get_line_count)

        self.get_line = get_line  # TODO: Add cache!
        self.get_line_count = get_line_count  # TODO: Add cache!
        self.line_processors = line_processors  # XXX: not sure whether it's this class' responsibility.

        self.cursor_position_line = 0
        self.cursor_position_column = 0





        cursor_pos = (7, 20)


