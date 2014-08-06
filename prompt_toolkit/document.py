"""
"""
from __future__ import unicode_literals

import re

__all__ = ('Document',)


# Regex for finding the "words" in documents. (We consider a group of alnum
# characters a word, but also a group of special characters a word, as long as
# it doesn't contain a space.)
_FIND_WORD_RE =  re.compile('([a-zA-Z0-9_]+|[^a-zA-Z0-9_\s]+)')


class Document(object):
    """
    This is a immutable class around the text and cursor position, and contains
    methods for querying this data, e.g. to give the text before the cursor.

    This class is usually instantiated by a :class:`~prompt_toolkit.line.Line`
    object, and accessed as the `document` property of that class.

    :param text: string
    :param cursor_position: int
    """
    __slots__ = ('text', 'cursor_position')

    def __init__(self, text='', cursor_position=0):
        self.text = text
        self.cursor_position = cursor_position

    @property
    def current_char(self):
        """ Return character under cursor, or None """
        return self._get_char_relative_to_cursor(0)

    @property
    def char_before_cursor(self):
        """ Return character before the cursor, or None """
        return self._get_char_relative_to_cursor(-1)

    @property
    def text_before_cursor(self):
        return self.text[:self.cursor_position:]

    @property
    def text_after_cursor(self):
        return self.text[self.cursor_position:]

    @property
    def current_line_before_cursor(self):
        """ Text from the start of the line until the cursor. """
        return self.text_before_cursor.split('\n')[-1]

    @property
    def current_line_after_cursor(self):
        """ Text from the cursor until the end of the line. """
        return self.text_after_cursor.split('\n')[0]

    @property
    def lines(self):
        """
        Array of all the lines.
        """
        return self.text.split('\n')

    @property
    def line_count(self):
        """ Return the number of lines in this document. If the document ends
        with a trailing \n, that counts as the beginning of a new line. """
        return len(self.lines)

    @property
    def current_line(self):
        """ Return the text on the line where the cursor is. (when the input
        consists of just one line, it equals `text`. """
        return self.current_line_before_cursor + self.current_line_after_cursor

    @property
    def leading_whitespace_in_current_line(self):
        """ The leading whitespace in the left margin of the current line.  """
        current_line = self.current_line
        length = len(current_line) - len(current_line.lstrip())
        return current_line[:length]

    def _get_char_relative_to_cursor(self, offset=0):
        """ Return character relative to cursor position, or None """
        try:
            return self.text[self.cursor_position + offset]
        except IndexError:
            return None

    @property
    def cursor_position_row(self):
        """
        Current row. (0-based.)
        """
        return len(self.text_before_cursor.split('\n')) - 1

    @property
    def cursor_position_col(self):
        """
        Current column. (0-based.)
        """
        return len(self.current_line_before_cursor)

    def translate_index_to_position(self, index):
        """
        Given an index for the text, return the corresponding (row, col) tuple.
        """
        text_before_position = self.text[:index]

        row = len(text_before_position.split('\n'))
        col = len(text_before_position.split('\n')[-1])

        return row, col

    @property
    def cursor_at_the_end(self):
        """ True when the cursor is at the end of the text. """
        return self.cursor_position == len(self.text)

    @property
    def cursor_at_the_end_of_line(self):
        """ True when the cursor is at the end of this line. """
        return self.cursor_position_col == len(self.current_line)

    def find(self, sub, in_current_line=False):
        """
        Find `text` after the cursor, return position relative to the cursor
        position. Return `None` if nothing was found.
        """
        if in_current_line:
            after_cursor = self.current_line_after_cursor[1:]
        else:
            after_cursor = self.text_after_cursor[1:]

        index = after_cursor.find(sub)

        if index >= 0:
            return index + 1

    def find_backwards(self, sub, in_current_line=False):
        """
        Find `text` before the cursor, return position relative to the cursor
        position. Return `None` if nothing was found.
        """
        if in_current_line:
            before_cursor = self.current_line_before_cursor
        else:
            before_cursor = self.text_before_cursor

        index = before_cursor.rfind(sub)

        if index >= 0:
            return index - len(before_cursor)

    def find_start_of_previous_word(self):
        """
        Return an index relative to the cursor position pointing to the start
        of the previous word. Return `None` if nothing was found.
        """
        # Reverse the text before the cursor, in order to do an efficient
        # backwards search.
        text_before_cursor = self.text_before_cursor[::-1]

        match = _FIND_WORD_RE.search(text_before_cursor)

        if match:
            return - match.end(1)

    def find_start_of_next_word(self): # TODO: rename to find_next_word_beginning
        """
        Return an index relative to the cursor position pointing to the start
        of the next word. Return `None` if nothing was found.
        """
        iterable = _FIND_WORD_RE.finditer(self.text_after_cursor)

        try:
            # Take first match, unless it's the word on which we're right now.
            result = next(iterable).start(1)

            if result > 0:
                return result
            else:
                return next(iterable).start(1)

        except StopIteration:
            pass

    def find_end_of_next_word(self): # TODO: rename to find_next_word_ending
        """
        Return an index relative to the cursor position pointing to the end
        of the next word. Return `None` if nothing was found.
        """
        iterable = _FIND_WORD_RE.finditer(self.text_after_cursor)

        try:
            return next(iterable).end(1)
        except StopIteration:
            pass
