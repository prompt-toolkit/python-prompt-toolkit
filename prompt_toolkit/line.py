"""
Data structures for the line input.
It holds the text, cursor position, history, etc...
"""
from __future__ import unicode_literals

from functools import wraps

from .code import Code
from .document import Document
from .enums import IncrementalSearchDirection
from .prompt import Prompt
from .render_context import RenderContext

import os
import tempfile
import subprocess

__all__ = (
        'Line',

        # Exceptions raised by the Line object.
        'Exit',
        'ReturnInput',
        'Abort',
)

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


class ClipboardDataType(object):
    """
    Depending on how data has been copied, it can be pasted differently.
    If a whole line is copied, it will always be inserted as a line (below or
    above thu current one). If a word has been copied, it wiss be pasted
    inline. So, if you copy a whole line, it will not be pasted in the middle
    of another line.
    """
    #: Several characters or words have been copied. They are pasted inline.
    CHARACTERS = 'characters'

    #: A whole line that has been copied. This will be pasted below or above
    #: the current line as a new line.
    LINES = 'lines'


class ClipboardData(object):
    """
    Text on the clipboard.

    :param text: string
    :param type: :class:`~.ClipboardDataType`
    """
    def __init__(self, text='', type=ClipboardDataType.CHARACTERS):
        self.text = text
        self.type = type


def _quit_reverse_search_when_called(func): # XXX: rename to: '_quit_incremental_search_when_called'
    """
    When this method of the `Line` object is called. Make sure to exit
    reverse/forward search mode.
    """
    @wraps(func)
    def wrapper(self, *a, **kw):
        self.exit_isearch()
        return func(self, *a, **kw)
    return wrapper


class CompletionState(object):
    def __init__(self, original_cursor_position=0, current_completions=None):
        #: Cursor position in the input where the completion started.
        self.original_cursor_position = original_cursor_position

        #: List of all the current Completion instances which are possible at
        #: this point.
        self.current_completions = current_completions or []

        #: Position in the `current_completions` array.
        self.complete_index = 0 # Position in the `_completions` array.

    @property
    def current_completion_text(self):
        return self.current_completions[self.complete_index].suffix


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

        #: The history. A list to which we only append.
        self._history_lines = [] # Implement loader (history.load/save)

        self._clipboard = ClipboardData()

        self.__cursor_position = 0

        #: Readline argument text (for displaying in the prompt.)
        #: https://www.gnu.org/software/bash/manual/html_node/Readline-Arguments.html
        self._arg_prompt_text = ''

        self.reset()

    def reset(self):
        self.cursor_position = 0

        # Incremental-search
        self.in_isearch = False # XXX: rename to in_isearch_mode
        self.isearch_direction = IncrementalSearchDirection.FORWARD

        self._isearch_text = ''
        self._before_isearch_cursor_position = 0
        self._before_isearch_working_index = 0

        # Complete browser
        self.in_complete_mode = False
        self.complete_state = None

        # Undo stack
        self._undo_stack = []# Stack of (text, cursor_position)

        #: The working lines. Similar to history, except that this can be
        #: modified. The user can press arrow_up and edit previous entries.
        #: Ctrl-C should reset this, and copy the whole history back in here.
        #: Enter should process the current command and append to the real
        #: history.
        self._working_lines = self._history_lines[:]
        self._working_lines.append('')
        self.__working_index = len(self._working_lines) - 1

    ### <getters/setters>

    @property
    def text(self):
        return self._working_lines[self._working_index]

    @text.setter
    def text(self, value):
        self._working_lines[self._working_index] = value

        # Always quit autocomplete mode when the cursor position changes.
        self.in_complete_mode = False

        self._text_changed()

    @property
    def cursor_position(self):
        return self.__cursor_position

    @cursor_position.setter
    def cursor_position(self, value):
        self.__cursor_position = value

        # Always quit autocomplete mode when the cursor position changes.
        self.in_complete_mode = False

    @property
    def _working_index(self):
        return self.__working_index

    @_working_index.setter
    def _working_index(self, value):
        # Always quit autocomplete mode when the working index changes.
        self.in_complete_mode = False

        self.__working_index = value
        self._text_changed()

    ### End of <getters/setters>

    def _text_changed(self):
        """
        Not implemented. Override to capture when the current visible text
        changes.
        """
        pass

    def save_to_undo_stack(self):
        """
        Safe current state (input text and cursor position), so that we can
        restore it by calling undo.
        """
        state = (self.text, self.cursor_position)

        # Safe if the text is different from the text at the top of the stack
        # is different.
        if not self._undo_stack or self._undo_stack[-1][0] != state[0]:
            self._undo_stack.append(state)

    def set_current_line(self, value):
        """
        Replace current line (Does not touch other lines in multi-line input.)
        """
        # Move cursor to start of line.
        self.cursor_to_start_of_line(after_whitespace=False)

        # Replace text
        self.delete_until_end_of_line()
        self.insert_text(value, move_cursor=False)

    def transform_lines(self, line_index_iterator, transform_callback):
        """
        Transforms the text on a range of lines.
        When the iterator yield an index not in the range of lines that the
        document contains, it skips them silently.

        To uppercase some lines::

            transform_lines(range(5,10), lambda text: text.upper())

        :param line_index_iterator: Iterator of line numbers (int)
        :param transform_callback: callable that takes the original text of a
                                   line, and return the new text for this line.
        """
        # Split lines
        lines = self.text.split('\n')

        # Apply transformation
        for index in line_index_iterator:
            try:
                lines[index] = transform_callback(lines[index])
            except IndexError:
                pass

        self.text = '\n'.join(lines)

    @property
    def document(self):
        """
        Return :class:`.Document` instance from the current text and cursor
        position.
        """
        # TODO: this can be cached as long self.text does not change.
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
        if self.document.cursor_position_col > 0:
            self.cursor_position -= 1

    @_quit_reverse_search_when_called
    def cursor_right(self):
        if not self.document.cursor_at_the_end_of_line:
            self.cursor_position += 1

    @_quit_reverse_search_when_called
    def cursor_up(self):
        """
        (for multiline edit). Move cursor to the previous line.
        """
        new_pos = self.document.cursor_up_position
        if new_pos is not None:
            self.cursor_position = new_pos

    @_quit_reverse_search_when_called
    def cursor_down(self):
        """
        (for multiline edit). Move cursor to the next line.
        """
        new_pos = self.document.cursor_down_position
        if new_pos is not None:
            self.cursor_position = new_pos

    @_quit_reverse_search_when_called
    def auto_up(self):
        """
        If we're not on the first line (of a multiline input) go a line up,
        otherwise go back in history.
        """
        if self.in_complete_mode:
            self.complete_previous()
        elif self.document.cursor_position_row > 0:
            self.cursor_up()
        else:
            self.history_backward()

    @_quit_reverse_search_when_called
    def auto_down(self):
        """
        If we're not on the last line (of a multiline input) go a line down,
        otherwise go forward in history.
        """
        if self.in_complete_mode:
            self.complete_next()
        elif self.document.cursor_position_row < self.document.line_count - 1:
            self.cursor_down()
        else:
            old_index = self._working_index
            self.history_forward()

            # If we moved to the next line, place the cursor at the beginning.
            if old_index != self._working_index:
                self.cursor_position = 0

    @_quit_reverse_search_when_called
    def cursor_word_back(self):
        """ Move the cursor to the start of the previous word. """
        # Move at least one character to the left.
        self.cursor_position += (self.document.find_start_of_previous_word() or 0)

    @_quit_reverse_search_when_called
    def cursor_word_forward(self):
        """ Move the cursor to the start of the following word. """
        self.cursor_position += (self.document.find_next_word_beginning() or 0)

    @_quit_reverse_search_when_called
    def cursor_to_end_of_word(self):
        """
        Move the cursor right before the last character of the next word
        ending.
        """
        end = self.document.find_next_word_ending(include_current_position=False)
        if end > 1:
            self.cursor_position += end - 1

    @_quit_reverse_search_when_called
    def cursor_to_end_of_line(self):
        """
        Move cursor to the end of the current line.
        """
        self.cursor_position += len(self.document.current_line_after_cursor)

    @_quit_reverse_search_when_called
    def cursor_to_start_of_line(self, after_whitespace=False):
        """ Move the cursor to the first character of the current line. """
        self.cursor_position -= len(self.document.current_line_before_cursor)

        if after_whitespace:
            text_after_cursor = self.document.current_line_after_cursor
            self.cursor_position += len(text_after_cursor) - len(text_after_cursor.lstrip())

    # NOTE: don't _quit_reverse_search_when_called: we can delete in i-search.
    def delete_character_before_cursor(self, count=1): # TODO: unittest return type
        """ Delete character before cursor, return deleted character. """
        assert count > 0
        deleted = ''

        if self.in_isearch:
            self._isearch_text = self._isearch_text[:-count]
        else:
            if self.cursor_position > 0:
                deleted = self.text[self.cursor_position - count:self.cursor_position]
                self.text = self.text[:self.cursor_position - count] + self.text[self.cursor_position:]
                self.cursor_position -= len(deleted)

        return deleted

    @_quit_reverse_search_when_called
    def delete(self, count=1): # TODO: unittest `count`
        """ Delete one character. Return deleted character. """
        if self.cursor_position < len(self.text):
            deleted = self.document.text_after_cursor[:count]
            self.text = self.text[:self.cursor_position] + \
                    self.text[self.cursor_position + len(deleted):]
            return deleted
        else:
            return ''

    @_quit_reverse_search_when_called
    def delete_word(self):
        """ Delete one word. Return deleted word. """
        to_delete = self.document.find_next_word_beginning()
        return self.delete(count=to_delete)

    @_quit_reverse_search_when_called
    def delete_word_before_cursor(self): # TODO: unittest
        """ Delete one word before cursor. Return deleted word. """
        to_delete = - (self.document.find_start_of_previous_word() or 0)
        return self.delete_character_before_cursor(to_delete)

    @_quit_reverse_search_when_called
    def delete_until_end(self):
        """ Delete all input until the end. Return deleted text. """
        deleted = self.text[self.cursor_position:]
        self.text = self.text[:self.cursor_position]
        return deleted

    @_quit_reverse_search_when_called
    def delete_until_end_of_line(self): # TODO: unittest.
        """
        Delete all input until the end of this line. Return deleted text.
        """
        to_delete = len(self.document.current_line_after_cursor)
        return self.delete(count=to_delete)

    @_quit_reverse_search_when_called
    def delete_from_start_of_line(self): # TODO: unittest.
        """
        Delete all input from the start of the line until the current
        character. Return deleted text.
        (Actually, this is the same as pressing backspace until the start of
        the line.)
        """
        to_delete = len(self.document.current_line_before_cursor)
        return self.delete_character_before_cursor(to_delete)

    @_quit_reverse_search_when_called
    def delete_current_line(self):
        """
        Delete current line. Return deleted text.
        """
        document = self.document

        # Remember deleted text.
        deleted = document.current_line

        # Cut line.
        lines = document.lines
        pos = document.cursor_position_row
        self.text = '\n'.join(lines[:pos] + lines[pos+1:])

        # Move cursor.
        before_cursor = document.current_line_before_cursor
        self.cursor_position -= len(before_cursor)
        self.cursor_to_start_of_line(after_whitespace=True)

        return deleted

    @_quit_reverse_search_when_called
    def join_next_line(self):
        """
        Join the next line to the current one by deleting the line ending after
        the current line.
        """
        self.cursor_to_end_of_line()
        self.delete()

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

    @_quit_reverse_search_when_called
    def go_to_substring(self, sub, in_current_line=False, backwards=False):
        """
        Find next occurence of this substring, and move cursor position there.
        """
        if backwards:
            index = self.document.find_backwards(sub, in_current_line=in_current_line)
        else:
            index = self.document.find(sub, in_current_line=in_current_line)

        if index:
            self.cursor_position += index

    @_quit_reverse_search_when_called
    def go_to_column(self, column):
        """
        Go to this column on the current line. (Go to the end column > length
        of the line.)
        """
        line_length = len(self.document.current_line)
        current_column = self.document.cursor_position_col
        column = max(0, min(line_length, column))

        self.cursor_position += column - current_column

    def _create_code_obj(self):
        return self.code_cls(self.document)

    @_quit_reverse_search_when_called
    def list_completions(self):
        """
        Get and show all completions
        """
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

    @_quit_reverse_search_when_called
    def complete_next(self):
        """
        Enter complete mode and browse through the completions.
        """
        if not self.in_complete_mode:
            self._start_complete()
        else:
            index = (self.complete_state.complete_index + 1) % len(self.complete_state.current_completions)
            self._go_to_completion(index)

    @_quit_reverse_search_when_called
    def complete_previous(self):
        """
        Enter complete mode and browse through the completions.
        """
        if not self.in_complete_mode:
            self._start_complete()

        index = (self.complete_state.complete_index - 1) % len(self.complete_state.current_completions)
        self._go_to_completion(index)


    def _start_complete(self):
        """
        Start completions. (Generate list of completions and initialize.)
        """
        # Generate list of all completions.
        current_completions = list(self._create_code_obj().get_completions())

        if current_completions:
            self.complete_state = CompletionState(
                        original_cursor_position=self.cursor_position,
                        current_completions=current_completions)
            self.insert_text(self.complete_state.current_completion_text)
            self.in_complete_mode = True

        else:
            self.in_complete_mode = False
            self.complete_state = None

    def _go_to_completion(self, index):
        """
        Select a completion from the list of current completions.
        """
        assert self.in_complete_mode

        # Undo previous completion
        count = len(self.complete_state.current_completion_text)
        if count:
            self.delete_character_before_cursor(count=len(self.complete_state.current_completion_text))

        # Set new completion
        self.complete_state.complete_index = index
        self.insert_text(self.complete_state.current_completion_text)

        self.in_complete_mode = True

    def get_render_context(self, _abort=False, _accept=False):
        """
        Return a `RenderContext` object, to pass the current state to the renderer.
        """
        if self.in_isearch:
            # In case of reverse search, render reverse search prompt.
            code = self.code_cls(self.document)

            if self.document.has_match_at_current_position(self._isearch_text):
                highlight_regions = [
                        (self.document.translate_index_to_position(self.cursor_position),
                        self.document.translate_index_to_position(self.cursor_position + len(self._isearch_text))) ]
            else:
                highlight_regions = [ ]

        else:
            code = self._create_code_obj()
            highlight_regions = [ ]

        # Create prompt instance.
        prompt = self.prompt_cls(self, code)

        return RenderContext(prompt, code, highlight_regions=highlight_regions,
                        complete_state=self.complete_state,
                        abort=_abort, accept=_accept)

    @_quit_reverse_search_when_called
    def history_forward(self):
        if self._working_index < len(self._working_lines) - 1:
            # Go forward in history, and update cursor_position.
            self._working_index += 1
            self.cursor_position = len(self.text)

    @_quit_reverse_search_when_called
    def history_backward(self):
        if self._working_index > 0:
            # Go back in history, and update cursor_position.
            self._working_index -= 1
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

    def insert_text(self, data, overwrite=False, move_cursor=True):
        """
        Insert characters at cursor position.
        """
        if self.in_isearch:
            self._isearch_text += data

            if not self.document.has_match_at_current_position(self._isearch_text):
                self.search_next(self.isearch_direction)
        else:
            # In insert/text mode.
            if overwrite:
                # Don't overwrite the newline itself. Just before the line ending, it should act like insert mode.
                overwritten_text = self.text[self.cursor_position:self.cursor_position+len(data)]
                if '\n' in overwritten_text:
                    overwritten_text = overwritten_text[:overwritten_text.find('\n')]

                self.text = self.text[:self.cursor_position] + data + self.text[self.cursor_position+len(overwritten_text):]
            else:
                self.text = self.text[:self.cursor_position] + data + self.text[self.cursor_position:]

            if move_cursor:
                self.cursor_position += len(data)

    def set_clipboard(self, clipboard_data):
        """
        Set data to the clipboard.

        :param clipboard_data: :class:`~.ClipboardData` instance.
        """
        self._clipboard = clipboard_data

    @_quit_reverse_search_when_called
    def paste_from_clipboard(self, before=False):
        """
        Insert the data from the clipboard.
        """
        if self._clipboard and self._clipboard.text:
            if self._clipboard.type == ClipboardDataType.CHARACTERS:
                if before:
                    self.insert_text(self._clipboard.text)
                else:
                    self.cursor_right()
                    self.insert_text(self._clipboard.text)
                    self.cursor_left()

            elif self._clipboard.type == ClipboardDataType.LINES:
                if before:
                    self.cursor_to_start_of_line()
                    self.insert_text(self._clipboard.text + '\n', move_cursor=False)
                else:
                    self.cursor_to_end_of_line()
                    self.insert_text('\n')
                    self.insert_text(self._clipboard.text, move_cursor=False)

    @_quit_reverse_search_when_called
    def undo(self):
        if self._undo_stack:
            text, pos = self._undo_stack.pop()

            self.text = text
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

        # Save at the tail of the history. (But don't if the last entry the
        # history is already the same.)
        if not self._history_lines or self._history_lines[-1] != text:
            self._history_lines.append(text)

        render_context = self.get_render_context(_accept=True)

        self.reset()
        raise ReturnInput(code, render_context)

    def reverse_search(self):
        """
        Enter i-search mode, or if already entered, go to the previous match.
        """
        self.isearch_direction = IncrementalSearchDirection.BACKWARD

        if self.in_isearch:
            self.search_next(self.isearch_direction)
        else:
            self._start_isearch()

    def forward_search(self):
        """
        Enter i-search mode, or if already entered, go to the following match.
        """
        self.isearch_direction = IncrementalSearchDirection.FORWARD

        if self.in_isearch:
            self.search_next(self.isearch_direction)
        else:
            self._start_isearch()

    def _start_isearch(self):
        self.in_isearch = True
        self._isearch_text = ''

        self._before_isearch_cursor_position = self.cursor_position
        self._before_isearch_working_index = self._working_index

    def search_next(self, direction):
        if not self._isearch_text:
            return

        if direction == IncrementalSearchDirection.BACKWARD:
            # Try find at the current input.
            new_index = self.document.find_backwards(self._isearch_text)

            if new_index is not None:
                self.cursor_position += new_index
            else:
                # No match, go back in the history.
                for i in range(len(self._working_lines)):
                    i2 = (self._working_index - i - 1) % len(self._working_lines)
                    document = Document(self._working_lines[i2], len(self._working_lines[i2]))
                    new_index = document.find_backwards(self._isearch_text)
                    if new_index is not None:
                        self._working_index = i2
                        self.cursor_position = len(self._working_lines[i2]) + new_index
                        break
        else:
            # Try find at the current input.
            new_index = self.document.find(self._isearch_text)

            if new_index is not None:
                self.cursor_position += new_index
            else:
                # No match, go forward in the history.
                for i in range(len(self._working_lines)):
                    i2 = (self._working_index + i + 1) % len(self._working_lines)
                    document = Document(self._working_lines[i2], 0)
                    new_index = document.find(self._isearch_text, include_current_position=True)
                    if new_index is not None:
                        self._working_index = i2
                        self.cursor_position = new_index
                        break

    def exit_isearch(self, restore_original_line=False):
        """
        Exit i-search mode.
        """
        if self.in_isearch:
            if restore_original_line:
                self._before_isearch_cursor_position = self.cursor_position
                self._working_index = self._before_isearch_working_index

            self.in_isearch = False

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
            self.text = f.read().decode('utf-8')
        self.cursor_position = len(self.text)

        # Clean up temp file.
        os.remove(filename)

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
