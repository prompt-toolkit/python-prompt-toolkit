"""
Data structures for the line input.
It holds the text, cursor position, history, etc...
"""
from __future__ import unicode_literals

from functools import wraps

from .render_context import RenderContext
from .code import Code
from .prompt import Prompt
from .enums import ReverseSearchDirection

import os
import tempfile
import subprocess


class Exit(Exception):
    def __init__(self, render_context):
        self.render_context = render_context


class ReturnInput(Exception):
    def __init__(self, document, render_context):
        self.document = document
        self.render_context = render_context


class Abort(Exception):
    def __init__(self, render_context):
        self.render_context = render_context


class Document(object):
    """
    Immutable class around Text & cursor position.
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

    @property
    def current_line_position(self):
        """ Report the line number of our cursor. (0 when we are on the first line.) """
        return len(self.text_before_cursor.split('\n')) - 1
            # TODO: maybe deprecate: use cursor_position_row

    def _get_char_relative_to_cursor(self, offset=0):
        """ Return character relative to cursor position, or None """
        try:
            return self.text[self.cursor_position + offset]
        except IndexError:
            return None

    @property
    def cursor_position_row(self):
        return len(self.text_before_cursor.split('\n'))

    @property
    def cursor_position_col(self):
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


def _quit_reverse_search_when_called(func):
    """
    When this method of the `Line` object is called. Make sure to exit
    reverse/forward search mode.
    """
    @wraps(func)
    def wrapper(self, *a, **kw):
        self.exit_isearch()
        return func(self, *a, **kw)
    return wrapper


class Line(object):
    """
    Data structure that holds the text and cursor position of the current input
    line and implements all text manupulations on top of it. It also implements
    the history and undo stack, and reverse search.

    :attr code_cls: :class:`~prompt_toolkit.code.CodeBase` class.
    :attr prompt_cls: :class:`~prompt_toolkit.prompt.PromptBase` class.
    """
    def __init__(self, renderer=None, code_cls=Code, prompt_cls=Prompt):
        self.renderer = renderer
        self.code_cls = code_cls
        self.prompt_cls = prompt_cls
        self._history_lines = [] # Implement loader (history.load/save)

        #: Readline argument text (for displaying in the prompt.)
        #: https://www.gnu.org/software/bash/manual/html_node/Readline-Arguments.html
        self._arg_prompt_text = ''

        self.reset()

    def reset(self):
        self.cursor_position = 0
        self._in_isearch = False
        self._isearch_text = ''
        self._isearch_direction = ReverseSearchDirection.FORWARD
        self._undo_stack = [] # Stack of (text, cursor_position)

        # Start new, empty input.
        if len(self._history_lines) == 0 or self._history_lines[-1] != '':
            self._history_lines.append('')
        self._history_index = len(self._history_lines) - 1

        #: The current text (we edit here instead of `_history_lines[_history_index]`)
        self._text = ''

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self.set_text(value)

    def set_text(self, value, safe_current_in_undo_buffer=True):
        # Remember current text in the undo stack.
        if safe_current_in_undo_buffer:
            self._undo_stack.append((self.text, self.cursor_position))

        self._text = value

    @property
    def document(self):
        """ Return :class:`.Document` instance from the current text and cursor
        position. """
        return Document(self.text, self.cursor_position)

    def set_arg_prompt(self, arg):
        """
        Called from the `InputStreamHandler` to set a "(arg: x)"-like prompt.
        (Both in Vi and Emacs-mode we have a way to repeat line operations.
        Settings this attribute to the `Line` object allows the prompt/renderer
        to visualise it.)
        """
        self._arg_prompt_text = arg

    @_quit_reverse_search_when_called
    def home(self):
        self.cursor_position = 0

    @_quit_reverse_search_when_called
    def end(self):
        self.cursor_position = len(self.text)

    @_quit_reverse_search_when_called
    def cursor_left(self):
        if self.cursor_position > 0:
            self.cursor_position -= 1

    @_quit_reverse_search_when_called
    def cursor_right(self):
        if self.cursor_position < len(self.text):
            self.cursor_position += 1

    @_quit_reverse_search_when_called
    def cursor_up(self):
        """
        (only for multiline edit). Move cursor to the previous line.
        """
        document = self.document

        if '\n' in document.text_before_cursor:
            lines = document.text_before_cursor.split('\n')
            current_line = lines[-1] # before the cursor
            previous_line = lines[-2]

            # When the current line is longer then the previous, move to the
            # last character of the previous line.
            if len(current_line) > len(previous_line):
                self.cursor_position -= len(current_line) + 1

            # Otherwise find the corresponding position in the previous line.
            else:
                self.cursor_position -= len(previous_line) + 1

    @_quit_reverse_search_when_called
    def cursor_down(self):
        """
        (only for multiline edit). Move cursor to the next line.
        """
        document = self.document

        if '\n' in document.text_after_cursor:
            pos = len(document.text_before_cursor.split('\n')[-1])
            lines = document.text_after_cursor.split('\n')
            current_line = lines[0] # after the cursor
            next_line = lines[1]

            # When the current line is longer then the previous, move to the
            # last character of the next line.
            if pos > len(next_line):
                self.cursor_position += len(current_line) + len(next_line) + 1

            # Otherwise find the corresponding position in the next line.
            else:
                self.cursor_position += len(current_line) + pos + 1

    @_quit_reverse_search_when_called
    def auto_up(self):
        """
        If we're not on the first line (of a multiline input) go a line up,
        otherwise go back in history.
        """
        if self.document.cursor_position_row > 1:
            self.cursor_up()
        else:
            self.history_backward()

    @_quit_reverse_search_when_called
    def auto_down(self):
        """
        If we're not on the last line (of a multiline input) go a line down,
        otherwise go forward in history.
        """
        if self.document.cursor_position_row < self.document.line_count:
            self.cursor_down()
        else:
            old_index = self._history_index
            self.history_forward()

            # If we moved to the next line, place the cursor at the beginning.
            if old_index != self._history_index:
                self.cursor_position = 0

    @_quit_reverse_search_when_called
    def cursor_word_back(self):
        """ Move the cursor to the start of the previous word. """
        # Move at least one character to the left.
        self.cursor_left()

        # Move over whitespace.
        while self.cursor_position > 0 and (self.document.current_char or ' ').isspace():
            self.cursor_left()

        # Move to beginning of word.
        while self.cursor_position > 0 and not (self.document._get_char_relative_to_cursor(-1) or 'x').isspace():
            self.cursor_left()

    @_quit_reverse_search_when_called
    def cursor_word_forward(self):
        """ Move the cursor to the start of the following word. """
        # Move at least one character to the right.
        self.cursor_right()

        # Move over word characters.
        while self.cursor_position < len(self.text) and not (self.document.current_char or ' ').isspace():
            self.cursor_right()

        # Move over whitespace to the start of the next word.
        while self.cursor_position < len(self.text) and (self.document.current_char or 'x').isspace():
            self.cursor_right()

    @_quit_reverse_search_when_called
    def cursor_to_end_of_line(self):
        while self.document.current_char and self.document.current_char != '\n':
            self.cursor_right()

    @_quit_reverse_search_when_called
    def cursor_to_start_of_line(self, after_whitespace=False):
        while self.cursor_position > 0 and self.document._get_char_relative_to_cursor(-1) != '\n':
            self.cursor_left()

        # When the `after_whitespace` flag is `True`, ignore the whitespace at
        # the start of the line.
        if after_whitespace:
            while self.document.current_char.isspace():
                self.cursor_right()

    def delete_character_before_cursor(self):
        if self._in_isearch:
            self._isearch_text = self._isearch_text[:-1]
        else:
            if self.cursor_position > 0:
                self.text = self.text[:self.cursor_position - 1] + self.text[self.cursor_position:]
                self.cursor_position -= 1

    @_quit_reverse_search_when_called
    def delete(self):
        """ Delete one character. Return deleted character. """
        if self.cursor_position < len(self.text):
            deleted = self.document.current_char
            self.text = self.text[:self.cursor_position] + self.text[self.cursor_position+1:]
            return deleted
        else:
            return ''

    @_quit_reverse_search_when_called
    def delete_word(self):
        """ Delete one word. Return deleted word. """
        deleted = ''

        # Delete word after cursor.
        while self.document.current_char and self.document.current_char.isalnum():
            # Delete word first.
            deleted += self.delete()

        while self.document.current_char and self.document.current_char.isspace():
            # Delete whitespace after word.
            deleted += self.delete()

        return deleted

    @_quit_reverse_search_when_called
    def delete_until_end(self):
        """ Delete all input until the end. Return deleted text. """
        deleted = self.text[self.cursor_position:]
        self.text = self.text[:self.cursor_position]
        return deleted

    @_quit_reverse_search_when_called
    def delete_until_end_of_line(self):
        """ Delete all input until the end of this line. Return deleted text. """
        endpos = self.text[self.cursor_position:].find('\n')
        if endpos == -1:
            endpos = None
        else:
            endpos += self.cursor_position

        deleted = self.text[self.cursor_position:endpos]
        self.text = self.text[:self.cursor_position] + ('' if endpos is None else self.text[endpos:])
        self.cursor_position -= 1
        return deleted

    @_quit_reverse_search_when_called
    def delete_current_line(self):
        """ Delete current line. Return deleted text. """
        document = self.document

        # Remember deleted text
        deleted = document.current_line

        lines = document.lines
        pos = document.current_line_position

        self.text = '\n'.join(lines[:pos] + lines[pos+1:])
        return deleted + '\n'

    @_quit_reverse_search_when_called
    def join_next_line(self):
        """ Join the next line to the current one by deleting the line ending
        after the current line. """
        # Find the first \n after the cursor
        after_cursor = self.document.text_after_cursor
        i = after_cursor.index('\n')

        self.text = self.document.text_before_cursor + after_cursor[:i] + after_cursor[i+1:]

    @_quit_reverse_search_when_called
    def swap_characters_before_cursor(self):
        """
        Swap the last two characters before the cursor.
        """
        pos = self.cursor_position

        if pos >= 2:
            a = self.text[pos - 2]
            b = self.text[pos - 1]

            self.text = self.text[:pos-2] + b + a + self.text[pos:]

    @_quit_reverse_search_when_called
    def go_to_matching_bracket(self):
        """ Go to matching [, (, { or < bracket. """
        stack = 1

        for A, B in '()', '[]', '{}', '<>':
            if self.document.current_char == A:
                for i, c in enumerate(self.document.text_after_cursor[1:]):
                    if c == A: stack += 1
                    elif c == B: stack -= 1

                    if stack == 0:
                        self.cursor_position += (i + 1)
                        break

            elif self.document.current_char == B:
                for i, c in enumerate(reversed(self.document.text_before_cursor)):
                    if c == B: stack += 1
                    elif c == A: stack -= 1

                    if stack == 0:
                        self.cursor_position -= (i + 1)
                        break

    def _create_code_obj(self):
        return self.code_cls(self.document)

    @_quit_reverse_search_when_called
    def list_completions(self):
        # Get and show all completions
        results = list(self._create_code_obj().get_completions())

        if results and self.renderer:
            self.renderer.render_completions(results)

    @_quit_reverse_search_when_called
    def complete(self):
        """ Autocomplete.
        Returns true if there was a completion. """
        # On the first tab press, try to find one completion and complete.
        result = self._create_code_obj().complete()
        if result:
            self.text = self.text[:self.cursor_position] + result + self.text[self.cursor_position:]
            self.cursor_position += len(result)
            return True
        else:
            return False

    def get_render_context(self, _abort=False, _accept=False):
        """
        Return a `RenderContext` object, to pass the current state to the renderer.
        """
        if self._in_isearch:
            # In case of reverse search, render reverse search prompt.
            if self._in_isearch_history_index < len(self._history_lines):
                line = self._history_lines[self._in_isearch_history_index]
                pos = max(0, self._history_lines[self._in_isearch_history_index].find(
                                self._isearch_text))
            else:
                line = ''
                pos = 0

            document = Document(line, pos)
            code = self.code_cls(document)

            if line:
                highlight_regions = [
                    (document.translate_index_to_position(pos),
                    document.translate_index_to_position(pos + len(self._isearch_text))) ]
            else:
                highlight_regions = [ ]

        else:
            code = self._create_code_obj()
            highlight_regions = [ ]

        # Create prompt instance.
        prompt = self.prompt_cls(self, code)

        return RenderContext(prompt, code, highlight_regions=highlight_regions,
                        abort=_abort, accept=_accept)

    @_quit_reverse_search_when_called
    def history_forward(self):
        if self._history_index < len(self._history_lines) - 1:
            # Save current edited text in history.
            if self._text:
                self._history_lines[self._history_index] = self._text

            # Go back in history, and update _text/cursor_position.
            self._history_index += 1
            self.set_text(self._history_lines[self._history_index],
                                    safe_current_in_undo_buffer=False)
            self.cursor_position = len(self.text)

    @_quit_reverse_search_when_called
    def history_backward(self):
        if self._history_index > 0:
            # Save current edited text in history.
            if self._text:
                self._history_lines[self._history_index] = self._text

            # Go back in history, and update _text/cursor_position.
            self._history_index -= 1
            self.set_text(self._history_lines[self._history_index],
                                    safe_current_in_undo_buffer=False)
            self.cursor_position = len(self.text)

    @_quit_reverse_search_when_called
    def newline(self):
        self.insert_text('\n')

    def insert_line_above(self, copy_margin=True):
        """
        Insert a new line above the current one.
        """
        if copy_margin:
            insert = self.document.leading_whitespace_in_current_line + '\n'
        else:
            insert = '\n'

        self.cursor_to_start_of_line()
        self.insert_text(insert)
        self.cursor_position -= 1

    def insert_line_below(self, copy_margin=True):
        """
        Insert a new line below the current one.
        """
        if copy_margin:
            insert = '\n' + self.document.leading_whitespace_in_current_line
        else:
            insert = '\n'

        self.cursor_to_end_of_line()
        self.insert_text(insert)

    def insert_text(self, data, overwrite=False, safe_current_in_undo_buffer=True):
        """
        Insert characters at cursor position.
        """
        if self._in_isearch:
            self._isearch_text += data

            if self._isearch_text not in self._history_lines[self._in_isearch_history_index]:
                if self._isearch_direction == ReverseSearchDirection.BACKWARD:
                    self.reverse_search()
                else:
                    self.forward_search()

        else:
            # In insert/text mode.
            set_text = lambda value: self.set_text(value, safe_current_in_undo_buffer)

            if overwrite:
                set_text(self.text[:self.cursor_position] + data + self.text[self.cursor_position+len(data):])
            else:
                set_text(self.text[:self.cursor_position] + data + self.text[self.cursor_position:])

            self.cursor_position += len(data)

    def undo(self):
        if self._undo_stack:
            text, pos = self._undo_stack.pop()

            self.set_text(text, safe_current_in_undo_buffer=False)
            self.cursor_position = pos

    @_quit_reverse_search_when_called
    def abort(self):
        """
        Abort input. (Probably Ctrl-C press)
        """
        render_context = self.get_render_context(_abort=True)

        self.reset()
        raise Abort(render_context)

    @_quit_reverse_search_when_called
    def exit(self):
        """
        Quit command line. (Probably Ctrl-D press.)
        """
        render_context = self.get_render_context(_abort=True)
        raise Exit(render_context)

    @_quit_reverse_search_when_called
    def return_input(self):
        """
        Return the current line to the `CommandLine.read_input` call.
        """
        code = self._create_code_obj()
        text = self.text

        # Save at the tail of the history. (But remove tail if we have a
        # duplate entry in the history.)
        self._history_lines[-1] = text
        if len(self._history_lines) > 1 and self._history_lines[-1] == self._history_lines[-2]:
            self._history_lines.pop()

        render_context = self.get_render_context(_accept=True)

        self.reset()
        raise ReturnInput(code, render_context)

    def reverse_search(self):
        """
        Enter i-search mode, or if already entered, go to the previous match.
        """
        self._isearch_direction = ReverseSearchDirection.BACKWARD

        if self._in_isearch:
            # Go looking for something in the history matching this text.
            for i in range(len(self._history_lines)):
                i2 = (self._in_isearch_history_index - 1 - i) % len(self._history_lines)
                if self._isearch_text in self._history_lines[i2]:
                    self._in_isearch_history_index = i2
                    break
        else:
            self._in_isearch = True
            self._in_isearch_history_index = len(self._history_lines) - 1

    def forward_search(self):
        """
        Enter i-search mode, or if already entered, go to the following match.
        """
        self._isearch_direction = ReverseSearchDirection.FORWARD

        if self._in_isearch:
            # Go looking for something in the history matching this text.
            for i in range(len(self._history_lines)):
                i2 = (self._in_isearch_history_index + 1 + i) % len(self._history_lines)
                if self._isearch_text in self._history_lines[i2]:
                    self._in_isearch_history_index = i2
                    break
        else:
            self._in_isearch = True
            self._in_isearch_history_index = len(self._history_lines) - 1

    def exit_isearch(self, restore_original_line=False):
        """
        Exit i-search mode.
        """
        if self._in_isearch:
            if not restore_original_line:
                # Take the matching line from the history.
                self.text = self._history_lines[self._in_isearch_history_index]
                self.cursor_position = len(self._isearch_text)

            self._in_isearch = False
            self._isearch_text = ''

    @_quit_reverse_search_when_called
    def clear(self):
        """
        Clear renderer screen, usually as a result of Ctrl-L.
        """
        if self.renderer:
            self.renderer.clear()

    @_quit_reverse_search_when_called
    def open_in_editor(self):
        """ Open code in editor. """
        # Write to temporary file
        descriptor, filename = tempfile.mkstemp()
        os.write(descriptor, self.text.encode('utf-8'))
        os.close(descriptor)

        # Open in editor
        self._open_file_in_editor(filename)

        # Read content again.
        with open(filename, 'rb') as f:
            self.set_text(f.read().decode('utf-8'))
        self.cursor_position = len(self.text)

    def _open_file_in_editor(self, filename):
        """ Call editor executable. """
        # If the 'EDITOR' environment variable has been set, use that one.
        # Otherwise, fall back to the first available editor that we can find.
        editor = os.environ.get('EDITOR')

        editors = [
                editor,

                # Order of preference.
                '/usr/bin/editor',
                '/usr/bin/nano',
                '/usr/bin/pico',
                '/usr/bin/vi',
                '/usr/bin/emacs',
        ]

        for e in editors:
            if e:
                if os.path.exists(e):
                    subprocess.call([e, filename])
                    return
