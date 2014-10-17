from __future__ import unicode_literals
from ..enums import IncrementalSearchDirection, InputMode
from ..keys import Keys
from ..line import ClipboardData, ClipboardDataType, SelectionType, indent, unindent
from ..selection import SelectionType

from .basic import basic_bindings
from .utils import create_handle_decorator

import codecs

__all__ = (
    'vi_bindings',
)


class CursorRegion(object):
    """
    Return struct for functions wrapped in ``change_delete_move_yank_handler``.
    """
    def __init__(self, start, end=0):
        self.start = start
        self.end = end

    def sorted(self):
        """
        Return a (start, end) tuple where start <= end.
        """
        if self.start < self.end:
            return self.start, self.end
        else:
            return self.end, self.start


def vi_bindings(registry, cli_ref):
    """
    Vi extensions.

    # Overview of Readline Vi commands:
    # http://www.catonmat.net/download/bash-vi-editing-mode-cheat-sheet.pdf
    """
    basic_bindings(registry, cli_ref)
    line = cli_ref().line
    search_line = cli_ref().lines['search']
    handle = create_handle_decorator(registry, line)

    _last_character_find = [None]  # (char, backwards) tuple
    _search_direction = [IncrementalSearchDirection.FORWARD]

    vi_transform_functions = [
        # Rot 13 transformation
        (('g', '?'), lambda string: codecs.encode(string, 'rot_13')),

        # To lowercase
        (('g', 'u'), lambda string: string.lower()),

        # To uppercase.
        (('g', 'U'), lambda string: string.upper()),

        # Swap case.
        # (XXX: If we would implement 'tildeop', the 'g' prefix is not required.)
        (('g', '~'), lambda string: string.swapcase()),
    ]

    @registry.add_after_handler_callback
    def check_cursor_position(event):
        """
        After every command, make sure that if we are in navigation mode, we
        never put the cursor after the last character of a line. (Unless it's
        an empty line.)
        """
        if (
                event.input_processor.input_mode == InputMode.VI_NAVIGATION and
                line.document.is_cursor_at_the_end_of_line and
                len(line.document.current_line) > 0):
            line.cursor_position -= 1

    @handle(Keys.Escape)
    def _(event):
        """
        Escape goes to vi navigation mode.
        """
        if event.input_processor.input_mode in (InputMode.INSERT,
                                                InputMode.VI_REPLACE):
            line.cursor_position += line.document.get_cursor_left_position()
        if event.input_processor.input_mode == InputMode.SELECTION:
            line.exit_selection()
            event.input_processor.pop_input_mode()
        else:
            event.input_processor.input_mode = InputMode.VI_NAVIGATION

    @handle(Keys.Up, in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Arrow up in navigation mode.
        """
        line.auto_up(count=event.arg)

    @handle(Keys.Down, in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Arrow down in navigation mode.
        """
        line.auto_down(count=event.arg)

    @handle(Keys.Backspace, in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        In navigation-mode, move cursor.
        """
        line.cursor_position += line.document.get_cursor_left_position(count=event.arg)

    @handle(Keys.ControlV, Keys.Any, in_mode=InputMode.INSERT)
    def _(event):
        """
        Insert a character literally (quoted insert).
        """
        line.insert_text(event.data, overwrite=False)

    @handle(Keys.ControlN, in_mode=InputMode.INSERT)
    def _(event):
        line.complete_next()

    @handle(Keys.ControlN, in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Control-N: Next completion.
        """
        line.auto_down()

    @handle(Keys.ControlP, in_mode=InputMode.INSERT)
    def _(event):
        """
        Control-P: To previous completion.
        """
        line.complete_previous()

    @handle(Keys.ControlY, in_mode=InputMode.INSERT)
    def _(event):
        """
        Accept current completion.
        """
        line.complete_state = None

    @handle(Keys.ControlE, in_mode=InputMode.INSERT)
    def _(event):
        """
        Cancel completion. Go back to originally typed text.
        """
        line.cancel_completion()

    @handle(Keys.ControlP, in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        CtrlP in navigation mode goes up.
        """
        line.auto_up()

    @handle(Keys.ControlJ, in_mode=InputMode.VI_NAVIGATION)
    @handle(Keys.ControlM, in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        In navigation mode, pressing enter will always return the input.
        """
        if line.validate():
            line.add_to_history()
            cli_ref().set_return_value(line.document)

    # ** In navigation mode **

    # List of navigation commands: http://hea-www.harvard.edu/~fine/Tech/vi.html

    @handle('a', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        line.cursor_position += line.document.get_cursor_right_position()
        event.input_processor.input_mode = InputMode.INSERT

    @handle('A', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        line.cursor_position += line.document.get_end_of_line_position()
        event.input_processor.input_mode = InputMode.INSERT

    @handle('C', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        # Change to end of line.
        # Same as 'c$' (which is implemented elsewhere.)
        """
        deleted = line.delete(count=line.document.get_end_of_line_position())
        if deleted:
            data = ClipboardData(deleted)
            line.set_clipboard(data)
        event.input_processor.input_mode = InputMode.INSERT

    @handle('c', 'c', in_mode=InputMode.VI_NAVIGATION)
    @handle('S', in_mode=InputMode.VI_NAVIGATION)
    def _(event):  # TODO: implement 'arg'
        """
        Change current line
        """
        # We copy the whole line.
        data = ClipboardData(line.document.current_line, ClipboardDataType.LINES)
        line.set_clipboard(data)

        # But we delete after the whitespace
        line.cursor_position += line.document.get_start_of_line_position(after_whitespace=True)
        line.delete(count=line.document.get_end_of_line_position())
        event.input_processor.input_mode = InputMode.INSERT

    @handle('D', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        deleted = line.delete(count=line.document.get_end_of_line_position())
        line.set_clipboard(ClipboardData(deleted))

    @handle('d', 'd', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Delete line. (Or the following 'n' lines.)
        """
        # Split string in before/deleted/after text.
        lines = line.document.lines

        before = '\n'.join(lines[:line.document.cursor_position_row])
        deleted = '\n'.join(lines[line.document.cursor_position_row: line.document.cursor_position_row + event.arg])
        after = '\n'.join(lines[line.document.cursor_position_row + event.arg:])

        # Set new text.
        if before and after:
            before = before + '\n'

        line.text = before + after

        # Set cursor position. (At the start of the first 'after' line, after the leading whitespace.)
        line.cursor_position = len(before) + len(after) - len(after.lstrip(' '))

        # Set clipboard data
        line.set_clipboard(ClipboardData(deleted, ClipboardDataType.LINES))

    @handle('G', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        If an argument is given, move to this line in the  history. (for
        example, 15G) Otherwise, go the the last line of the current string.
        """
        # If an arg has been given explicitely.
        if event._arg:
            line.go_to_history(event.arg - 1)

        # Otherwise this goes to the last line of the file.
        else:
            line.cursor_position = len(line.text)

    @handle('i', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        event.input_processor.input_mode = InputMode.INSERT

    @handle('I', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        event.input_processor.input_mode = InputMode.INSERT
        line.cursor_position += line.document.get_start_of_line_position(after_whitespace=True)

    @handle('J', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        for i in range(event.arg):
            line.join_next_line()

    @handle('n', in_mode=InputMode.VI_NAVIGATION)
    def _(event):  # XXX: use `change_delete_move_yank_handler` and implement 'arg'
        """
        Search next.
        """
        line.incremental_search(_search_direction[0])

    @handle('N', in_mode=InputMode.VI_NAVIGATION)
    def _(event):  # TODO: use `change_delete_move_yank_handler` and implement 'arg'
        """
        Search previous.
        """
        if _search_direction[0] == IncrementalSearchDirection.BACKWARD:
            line.incremental_search(IncrementalSearchDirection.FORWARD)
        else:
            line.incremental_search(IncrementalSearchDirection.BACKWARD)

    @handle('p', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Paste after
        """
        for i in range(event.arg):
            line.paste_from_clipboard()

    @handle('P', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Paste before
        """
        for i in range(event.arg):
            line.paste_from_clipboard(before=True)

    @handle('r', Keys.Any, in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Replace single character under cursor
        """
        line.insert_text(event.data * event.arg, overwrite=True)
        line.cursor_position -= 1

    @handle('R', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Go to 'replace'-mode.
        """
        event.input_processor.input_mode = InputMode.VI_REPLACE

    @handle('s', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Substitute with new text
        (Delete character(s) and go to insert mode.)
        """
        data = ClipboardData(''.join(line.delete() for i in range(event.arg)))
        line.set_clipboard(data)
        event.input_processor.input_mode = InputMode.INSERT

    @handle('u', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        for i in range(event.arg):
            line.undo()

    @handle('v', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        line.open_in_editor()

    # @handle('v', in_mode=InputMode.VI_NAVIGATION)
    # def _(event):
    #     """
    #     Start characters selection.
    #     """
    #     line.start_selection(selection_type=SelectionType.CHARACTERS)
    #     event.input_processor.push_input_mode(InputMode.SELECTION)

    @handle('V', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Start lines selection.
        """
        line.start_selection(selection_type=SelectionType.LINES)
        event.input_processor.push_input_mode(InputMode.SELECTION)

    @handle('a', 'w', in_mode=InputMode.SELECTION)
    @handle('a', 'W', in_mode=InputMode.SELECTION)
    def _(event):
        """
        Switch from visual linewise mode to visual characterwise mode.
        """
        if line.selection_state and line.selection_state.type == SelectionType.LINES:
            line.selection_state.type = SelectionType.CHARACTERS

    @handle('x', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Delete character.
        """
        data = ClipboardData(line.delete(count=event.arg))
        line.set_clipboard(data)

    @handle('x', in_mode=InputMode.SELECTION)
    @handle('d', 'd', in_mode=InputMode.SELECTION)
    def _(event):
        """
        Cut selection.
        """
        selection_type = line.selection_state.type
        deleted = line.cut_selection()
        line.set_clipboard(ClipboardData(deleted, selection_type))
        event.input_processor.pop_input_mode()

    @handle('c', in_mode=InputMode.SELECTION)
    def _(event):
        """
        Change selection (cut and go to insert mode).
        """
        selection_type = line.selection_state.type
        deleted = line.cut_selection()
        line.set_clipboard(ClipboardData(deleted, selection_type))
        event.input_processor.pop_input_mode()
        event.input_processor.input_mode = InputMode.INSERT

    @handle('y', in_mode=InputMode.SELECTION)
    def _(event):
        """
        Copy selection.
        """
        selection_type = line.selection_state.type
        deleted = line.copy_selection()
        line.set_clipboard(ClipboardData(deleted, selection_type))
        event.input_processor.pop_input_mode()

    @handle('X', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        data = line.delete_before_cursor()
        line.set_clipboard(data)

    @handle('y', 'y', in_mode=InputMode.VI_NAVIGATION)
    @handle('Y', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Yank the whole line.
        """
        text = '\n'.join(line.document.lines_from_current[:event.arg])

        data = ClipboardData(text, ClipboardDataType.LINES)
        line.set_clipboard(data)

    @handle('+', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Move to first non whitespace of next line
        """
        line.cursor_position += line.document.get_cursor_down_position(count=event.arg)
        line.cursor_position += line.document.get_start_of_line_position(after_whitespace=True)

    @handle('-', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Move to first non whitespace of previous line
        """
        line.cursor_position += line.document.get_cursor_up_position(count=event.arg)
        line.cursor_position += line.document.get_start_of_line_position(after_whitespace=True)

    @handle('>', '>', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Indent lines.
        """
        current_row = line.document.cursor_position_row
        indent(line, current_row, current_row + event.arg)

    @handle('<', '<', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Unindent lines.
        """
        current_row = line.document.cursor_position_row
        unindent(line, current_row, current_row + event.arg)

    @handle('>', in_mode=InputMode.SELECTION)
    def _(event):
        """
        Indent selection
        """
        selection_type = line.selection_state.type
        if selection_type == SelectionType.LINES:
            from_, to = line.document.selection_range()
            from_, _ = line.document.translate_index_to_position(from_)
            to, _ = line.document.translate_index_to_position(to)

            indent(line, from_ - 1, to, count=event.arg)  # XXX: why does translate_index_to_position return 1-based indexing???
        event.input_processor.pop_input_mode()

    @handle('<', in_mode=InputMode.SELECTION)
    def _(event):
        """
        Unindent selection
        """
        selection_type = line.selection_state.type
        if selection_type == SelectionType.LINES:
            from_, to = line.document.selection_range()
            from_, _ = line.document.translate_index_to_position(from_)
            to, _ = line.document.translate_index_to_position(to)

            unindent(line, from_ - 1, to, count=event.arg)
        event.input_processor.pop_input_mode()

    @handle('O', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Open line above and enter insertion mode
        """
        line.insert_line_above()
        event.input_processor.input_mode = InputMode.INSERT

    @handle('o', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Open line below and enter insertion mode
        """
        line.insert_line_below()
        event.input_processor.input_mode = InputMode.INSERT

    @handle('~', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Reverse case of current character and move cursor forward.
        """
        c = line.document.current_char
        if c is not None and c != '\n':
            c = (c.upper() if c.islower() else c.lower())
            line.insert_text(c, overwrite=True)

    @handle('/', in_mode=InputMode.VI_NAVIGATION)
    @handle(Keys.ControlS, in_mode=InputMode.INSERT)
    @handle(Keys.ControlS, in_mode=InputMode.VI_NAVIGATION)
    @handle(Keys.ControlS, in_mode=InputMode.VI_SEARCH)
    def _(event):
        """
        Vi-style forward search.
        """
        _search_direction[0] = direction = IncrementalSearchDirection.FORWARD
        line.incremental_search(direction)

        if event.input_processor.input_mode != InputMode.VI_SEARCH:
            event.input_processor.push_input_mode(InputMode.VI_SEARCH)

    @handle('?', in_mode=InputMode.VI_NAVIGATION)
    @handle(Keys.ControlR, in_mode=InputMode.INSERT)
    @handle(Keys.ControlR, in_mode=InputMode.VI_NAVIGATION)
    @handle(Keys.ControlR, in_mode=InputMode.VI_SEARCH)
    def _(event):
        """
        Vi-style backward search.
        """
        _search_direction[0] = direction = IncrementalSearchDirection.BACKWARD
        line.incremental_search(direction)

        if event.input_processor.input_mode != InputMode.VI_SEARCH:
            event.input_processor.push_input_mode(InputMode.VI_SEARCH)

    @handle('#', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Go to previous occurence of this word.
        """
        pass

    @handle('*', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        Go to next occurence of this word.
        """
        pass

    @handle('(', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        # TODO: go to begin of sentence.
        pass

    @handle(')', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        # TODO: go to end of sentence.
        pass

    def change_delete_move_yank_handler(*keys, **kw):
        """
        Register a change/delete/move/yank handlers. e.g.  'dw'/'cw'/'w'/'yw'
        The decorated function should return a ``CursorRegion``.
        This decorator will create both the 'change', 'delete' and move variants,
        based on that ``CursorRegion``.
        """
        no_move_handler = kw.pop('no_move_handler', False)

        # TODO: Also do '>' and '<' indent/unindent operators.
        # TODO: Also "gq": text formatting
        #  See: :help motion.txt
        def decorator(func):
            if not no_move_handler:
                @handle(*keys, in_mode=InputMode.VI_NAVIGATION)
                @handle(*keys, in_mode=InputMode.SELECTION)
                def move(event):
                    """ Create move handler. """
                    region = func(event)
                    line.cursor_position += region.start

            def create_transform_handler(transform_func, *a):
                @handle(*(a + keys), in_mode=InputMode.VI_NAVIGATION)
                def _(event):
                    """ Apply transformation (uppercase, lowercase, rot13, swap case). """
                    region = func(event)
                    start, end = region.sorted()

                    # Transform.
                    line.transform_region(
                        line.cursor_position + start,
                        line.cursor_position + end,
                        transform_func)

                    # Move cursor
                    line.cursor_position += (region.end or region.start)

            for k, f in vi_transform_functions:
                create_transform_handler(f, *k)

            @handle('y', *keys, in_mode=InputMode.VI_NAVIGATION)
            def yank_handler(event):
                """ Create yank handler. """
                region = func(event)

                start, end = region.sorted()
                substring = line.text[line.cursor_position + start: line.cursor_position + end]

                if substring:
                    line.set_clipboard(ClipboardData(substring))

            def create(delete_only):
                """ Create delete and change handlers. """
                @handle('cd'[delete_only], *keys, in_mode=InputMode.VI_NAVIGATION)
                @handle('cd'[delete_only], *keys, in_mode=InputMode.VI_NAVIGATION)
                def _(event):
                    region = func(event)
                    deleted = ''

                    if region:
                        start, end = region.sorted()

                        # Move to the start of the region.
                        line.cursor_position += start

                        # Delete until end of region.
                        deleted = line.delete(count=end-start)

                    # Set deleted/changed text to clipboard.
                    if deleted:
                        line.set_clipboard(ClipboardData(''.join(deleted)))

                    # Only go back to insert mode in case of 'change'.
                    if not delete_only:
                        event.input_processor.input_mode = InputMode.INSERT

            create(True)
            create(False)
            return func
        return decorator

    @change_delete_move_yank_handler('b')
    def _(event):
        """ Move one word or token left. """
        return CursorRegion(line.document.find_start_of_previous_word(count=event.arg) or 0)

    @change_delete_move_yank_handler('B')
    def _(event):
        """ Move one non-blank word left """
        return CursorRegion(line.document.find_start_of_previous_word(count=event.arg, WORD=True) or 0)

    @change_delete_move_yank_handler('$')
    def key_dollar(event):
        """ 'c$', 'd$' and '$':  Delete/change/move until end of line. """
        return CursorRegion(line.document.get_end_of_line_position())

    @change_delete_move_yank_handler('w')
    def _(event):
        """ 'word' forward. 'cw', 'dw', 'w': Delete/change/move one word.  """
        return CursorRegion(line.document.find_next_word_beginning(count=event.arg) or
                            line.document.end_position)

    @change_delete_move_yank_handler('W')
    def _(event):
        """ 'WORD' forward. 'cW', 'dW', 'W': Delete/change/move one WORD.  """
        return CursorRegion(line.document.find_next_word_beginning(count=event.arg, WORD=True) or
                            line.document.end_position)

    @change_delete_move_yank_handler('e')
    def _(event):
        """ End of 'word': 'ce', 'de', 'e' """
        end = line.document.find_next_word_ending(count=event.arg)
        return CursorRegion(end - 1 if end else 0)

    @change_delete_move_yank_handler('E')
    def _(event):
        """ End of 'WORD': 'cE', 'dE', 'E' """
        end = line.document.find_next_word_ending(count=event.arg, WORD=True)
        return CursorRegion(end - 1 if end else 0)

    @change_delete_move_yank_handler('i', 'w', no_move_handler=True)
    def _(event):
        """ Inner 'word': ciw and diw """
        start, end = line.document.find_boundaries_of_current_word()
        return CursorRegion(start, end)

    @change_delete_move_yank_handler('a', 'w', no_move_handler=True)
    def _(event):
        """ A 'word': caw and daw """
        start, end = line.document.find_boundaries_of_current_word(include_trailing_whitespace=True)
        return CursorRegion(start, end)

    @change_delete_move_yank_handler('i', 'W', no_move_handler=True)
    def _(event):
        """ Inner 'WORD': ciW and diW """
        start, end = line.document.find_boundaries_of_current_word(WORD=True)
        return CursorRegion(start, end)

    @change_delete_move_yank_handler('a', 'W', no_move_handler=True)
    def _(event):
        """ A 'WORD': caw and daw """
        start, end = line.document.find_boundaries_of_current_word(WORD=True, include_trailing_whitespace=True)
        return CursorRegion(start, end)

    @change_delete_move_yank_handler('^')
    def key_circumflex(event):
        """ 'c^', 'd^' and '^': Soft start of line, after whitespace. """
        return CursorRegion(line.document.get_start_of_line_position(after_whitespace=True))

    @change_delete_move_yank_handler('0', no_move_handler=True)
    def key_zero(event):
        """
        'c0', 'd0': Hard start of line, before whitespace.
        (The move '0' key is implemented elsewhere, because a '0' could also change the `arg`.)
        """
        return CursorRegion(line.document.get_start_of_line_position(after_whitespace=False))

    def create_ci_ca_handles(ci_start, ci_end, inner):
                # TODO: 'dab', 'dib', (brackets or block) 'daB', 'diB', Braces.
                # TODO: 'dat', 'dit', (tags (like xml)
        """
        Delete/Change string between this start and stop character. But keep these characters.
        This implements all the ci", ci<, ci{, ci(, di", di<, ca", ca<, ... combinations.
        """
        @change_delete_move_yank_handler('ai'[inner], ci_start, no_move_handler=True)
        @change_delete_move_yank_handler('ai'[inner], ci_end, no_move_handler=True)
        def _(event):
            start = line.document.find_backwards(ci_start, in_current_line=True)
            end = line.document.find(ci_end, in_current_line=True)

            if start is not None and end is not None:
                offset = 0 if inner else 1
                return CursorRegion(start + 1 - offset, end + offset)

    for inner in (False, True):
        for ci_start, ci_end in [('"', '"'), ("'", "'"), ("`", "`"),
                                 ('[', ']'), ('<', '>'), ('{', '}'), ('(', ')')]:
            create_ci_ca_handles(ci_start, ci_end, inner)

    @change_delete_move_yank_handler('{')  # TODO: implement 'arg'
    def _(event):
        """
        Move to previous blank-line separated section.
        Implements '{', 'c{', 'd{', 'y{'
        """
        line_index = line.document.find_previous_matching_line(
            lambda text: not text or text.isspace())

        if line_index:
            index = line.document.get_cursor_up_position(count=-line_index)
        else:
            index = 0
        return CursorRegion(index)

    @change_delete_move_yank_handler('}')  # TODO: implement 'arg'
    def _(event):
        """
        Move to next blank-line separated section.
        Implements '}', 'c}', 'd}', 'y}'
        """
        line_index = line.document.find_next_matching_line(
            lambda text: not text or text.isspace())

        if line_index:
            index = line.document.get_cursor_down_position(count=line_index)
        else:
            index = 0

        return CursorRegion(index)

    @change_delete_move_yank_handler('f', Keys.Any)
    def _(event):
        """
        Go to next occurance of character. Typing 'fx' will move the
        cursor to the next occurance of character. 'x'.
        """
        _last_character_find[0] = (event.data, False)
        match = line.document.find(event.data, in_current_line=True, count=event.arg)
        return CursorRegion(match or 0)

    @change_delete_move_yank_handler('F', Keys.Any)
    def _(event):
        """
        Go to previous occurance of character. Typing 'Fx' will move the
        cursor to the previous occurance of character. 'x'.
        """
        _last_character_find[0] = (event.data, True)
        return CursorRegion(line.document.find_backwards(event.data, in_current_line=True, count=event.arg) or 0)

    @change_delete_move_yank_handler('t', Keys.Any)
    def _(event):
        """
        Move right to the next occurance of c, then one char backward.
        """
        _last_character_find[0] = (event.data, False)
        match = line.document.find(event.data, in_current_line=True, count=event.arg)
        return CursorRegion(match - 1 if match else 0)

    @change_delete_move_yank_handler('T', Keys.Any)
    def _(event):
        """
        Move left to the previous occurance of c, then one char forward.
        """
        _last_character_find[0] = (event.data, True)
        match = line.document.find_backwards(event.data, in_current_line=True, count=event.arg)
        return CursorRegion(match + 1 if match else 0)

    def repeat(reverse):
        """
        Create ',' and ';' commands.
        """
        @change_delete_move_yank_handler(',' if reverse else ';')
        def _(event):
            # Repeat the last 'f'/'F'/'t'/'T' command.
            pos = 0

            if _last_character_find[0]:
                char, backwards = _last_character_find[0]

                if reverse:
                    backwards = not backwards

                if backwards:
                    pos = line.document.find_backwards(char, in_current_line=True, count=event.arg)
                else:
                    pos = line.document.find(char, in_current_line=True, count=event.arg)
            return CursorRegion(pos or 0)
    repeat(True)
    repeat(False)

    @change_delete_move_yank_handler('h')
    @change_delete_move_yank_handler(Keys.Left)
    def _(event):
        """ Implements 'ch', 'dh', 'h': Cursor left. """
        return CursorRegion(line.document.get_cursor_left_position(count=event.arg))

    @change_delete_move_yank_handler('j')
    def _(event):
        """ Implements 'cj', 'dj', 'j', ... Cursor up. """
        return CursorRegion(line.document.get_cursor_down_position(count=event.arg))

    @change_delete_move_yank_handler('k')
    def _(event):
        """ Implements 'ck', 'dk', 'k', ... Cursor up. """
        return CursorRegion(line.document.get_cursor_up_position(count=event.arg))

    @change_delete_move_yank_handler('l')
    @change_delete_move_yank_handler(' ')
    @change_delete_move_yank_handler(Keys.Right)
    def _(event):
        """ Implements 'cl', 'dl', 'l', 'c ', 'd ', ' '. Cursor right. """
        return CursorRegion(line.document.get_cursor_right_position(count=event.arg))

    @change_delete_move_yank_handler('H')
    def _(event):
        """ Implements 'cH', 'dH', 'H'. """
        # Vi moves to the start of the visible region.
        # cursor position 0 is okay for us.
        return CursorRegion(-len(line.document.text_before_cursor))

    @change_delete_move_yank_handler('L')
    def _(event):
        # Vi moves to the end of the visible region.
        # cursor position 0 is okay for us.
        return CursorRegion(len(line.document.text_after_cursor))

    @change_delete_move_yank_handler('%')
    def _(event):
        """
        Implements 'c%', 'd%', '%, 'y%' (Move to corresponding bracket.)
        If an 'arg' has been given, go this this % position in the file.
        """
        if event._arg:
            # If 'arg' has been given, the meaning of % is to go to the 'x%'
            # row in the file.
            if 0 < event.arg <= 100:
                absolute_index = line.document.translate_row_col_to_index(
                    int(event.arg * line.document.line_count / 100), 0)
                return CursorRegion(absolute_index - line.document.cursor_position)
            else:
                return CursorRegion(0)  # Do nothing.

        else:
            # Move to the corresponding opening/closing bracket (()'s, []'s and {}'s).
            return CursorRegion(line.document.matching_bracket_position)

    @change_delete_move_yank_handler('|')
    def _(event):
        # Move to the n-th column (you may specify the argument n by typing
        # it on number keys, for example, 20|).
        return CursorRegion(line.document.get_column_cursor_position(event.arg))

    @change_delete_move_yank_handler('g', 'g')
    def _(event):
        """
        Implements 'gg', 'cgg', 'ygg'
        """
        # Move to the top of the input.
        return CursorRegion(line.document.home_position)

    @handle('!', in_mode=InputMode.VI_NAVIGATION)
    def _(event):
        """
        '!' opens the system prompt.
        """
        event.input_processor.push_input_mode(InputMode.SYSTEM)

    @handle(Keys.Any, in_mode=InputMode.VI_NAVIGATION)
    @handle(Keys.Any, in_mode=InputMode.SELECTION)
    def _(event):
        """
        Always handle numberics in navigation mode as arg.
        """
        if event.data in '123456789' or (event._arg and event.data == '0'):
            event.append_to_arg_count(event.data)
        elif event.data == '0':
            line.cursor_position += line.document.get_start_of_line_position(after_whitespace=False)

    @handle(Keys.Any, in_mode=InputMode.VI_REPLACE)
    def _(event):
        """
        Insert data at cursor position.
        """
        line.insert_text(event.data, overwrite=True)

    @handle(Keys.Any, in_mode=InputMode.VI_SEARCH)
    def _(event):
        """
        Insert text after the / or ? prompt.
        """
        search_line.insert_text(event.data)
        line.set_search_text(search_line.text)

    @handle(Keys.ControlJ, in_mode=InputMode.VI_SEARCH)
    @handle(Keys.ControlM, in_mode=InputMode.VI_SEARCH)
    def _(event):
        """
        Enter at the / or ? prompt.
        """
        # Add query to history of searh line.
        search_line.add_to_history()
        search_line.reset()

        # Go back to navigation mode.
        event.input_processor.pop_input_mode()

    @handle(Keys.Backspace, in_mode=InputMode.VI_SEARCH)
    def _(event):
        """
        Backspace at the vi-search prompt.
        """
        if search_line.text:
            search_line.delete_before_cursor()
            line.set_search_text(search_line.text)
        else:
            # If no text after the prompt, cancel search.
            line.exit_isearch(restore_original_line=True)
            search_line.reset()
            event.input_processor.pop_input_mode()

    @handle(Keys.Up, in_mode=InputMode.VI_SEARCH)
    def _(event):
        """
        Go to the previous history item at the search prompt.
        """
        search_line.auto_up()
        line.set_search_text(search_line.text)

    @handle(Keys.Down, in_mode=InputMode.VI_SEARCH)
    def _(event):
        """
        Go to the next history item at the search prompt.
        """
        search_line.auto_down()
        search_line.cursor_position = len(search_line.text)
        line.set_search_text(search_line.text)

    @handle(Keys.Left, in_mode=InputMode.VI_SEARCH)
    def _(event):
        """
        Arrow left at the search prompt.
        """
        search_line.cursor_left()

    @handle(Keys.Right, in_mode=InputMode.VI_SEARCH)
    def _(event):
        """
        Arrow right at the search prompt.
        """
        search_line.cursor_right()

    @handle(Keys.ControlC, in_mode=InputMode.VI_SEARCH)
    def _(event):
        """
        Cancel search.
        """
        line.exit_isearch(restore_original_line=True)
        search_line.reset()
        event.input_processor.pop_input_mode()

    def create_selection_transform_handler(keys, transform_func):
        """
        Apply transformation on selection (uppercase, lowercase, rot13, swap case).
        """
        @handle(*keys, in_mode=InputMode.SELECTION)
        def _(event):
            range = line.document.selection_range()
            if range:
                line.transform_region(range[0], range[1], transform_func)
            event.input_processor.pop_input_mode()

    for k, f in vi_transform_functions:
        create_selection_transform_handler(k, f)

    @handle(Keys.ControlX, Keys.ControlL, in_mode=InputMode.INSERT)
    def _(event):
        """
        Pressing the ControlX - ControlL sequence in Vi mode does line
        completion based on the other lines in the document and the history.
        """
        line.start_history_lines_completion()

    @handle(Keys.ControlX, Keys.ControlF, in_mode=InputMode.INSERT)
    def _(event):
        """
        Complete file names.
        """
        # TODO
        pass
