"""
"""
from __future__ import unicode_literals


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

    def get_following_words(self, count=1, consume_nonword_before=False): # TODO: unittest
        """
        Return the text porting that contains the `count` words following after
        the cursor.
        """
        text = self.text_after_cursor
        pos = 0

        def more_text():
            return pos < len(text)

        def current_isalnum():
            return text[pos].isalnum()

        for i in range(count):
            if consume_nonword_before:
                # Consume non-word characters
                while more_text() and not current_isalnum():
                    pos += 1

            # Consume word characters
            while more_text() and current_isalnum():
                pos += 1

            if not consume_nonword_before:
                # Consume non-word characters
                while more_text() and not current_isalnum():
                    pos += 1

        return text[:pos]
