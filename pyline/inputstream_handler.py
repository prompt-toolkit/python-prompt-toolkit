"""
An `InputStreamHandler` receive callbacks from an :class:`InputStream` instance,
(where each callback represents a keystroke.) The `InputStreamHandler` will
then do the correct manipulations on a `Line` object.

This module implements Vi and Emacs keybindings.
"""
from __future__ import unicode_literals
from .line import ReturnInput, Abort

__all__ = (
    'InputStreamHandler',
    'EmacsInputStreamHandler',
    'ViInputStreamHandler'
)


class InputStreamHandler(object):
    """
    This class has callbacks for an `InputStream`, and calls the appropriate
    actions on a Line object.
    """
    def __init__(self, line):
        self._line = line
        self._clipboard = ''
        self._reset()

    def _reset(self):
        #: True when the user pressed on the 'tab' key.
        self._second_tab = False

        #: The name of the last previous public function call.
        self._last_call = None

    def __call__(self, name, *a):
        if name != 'ctrl_i':
            self._second_tab = False

        # Call actual handler
        method = getattr(self, name, None)
        if method:
            try:
                method(*a)
            except (Abort, ReturnInput):
                # Reset state when the input has been accepted/aborted.
                self._reset()
                raise

        # Keep track of what the last called method was.
        if not name.startswith('_'):
            self._last_call = name

    def home(self):
        self._line.home()

    def end(self):
        self._line.end()

    # CTRL keys.

    def ctrl_a(self):
        self._line.home()

    def ctrl_b(self):
        self._line.cursor_left()

    def ctrl_c(self):
        self._line.abort()

    def ctrl_d(self):
        self._line.exit()

    def ctrl_e(self):
        self._line.end()

    def ctrl_f(self):
        self._line.cursor_right()

    def ctrl_g(self):
        """ Abort an incremental search and restore the original line """
        self._line.exit_isearch(restore_original_line=True)

    def ctrl_h(self):
        self._line.delete_character_before_cursor()

    def ctrl_i(self):
        r""" Ctrl-I is identical to "\t" """
        self.tab()

    def ctrl_j(self):
        """ Newline."""
        self.enter()

    def ctrl_k(self):
        self._clipboard = self._line.delete_until_end_of_line()

    def ctrl_l(self):
        self._line.clear()

    def ctrl_m(self):
        """ Carriage return """
        # Alias for newline.
        self.ctrl_j()

    def ctrl_n(self):
        self._line.history_forward()

    def ctrl_o(self):
        pass

    def ctrl_p(self):
        self._line.history_backward()

    def ctrl_q(self):
        pass

    def ctrl_r(self):
        self._line.reverse_search()

    def ctrl_s(self):
        self._line.forward_search()

    def ctrl_t(self):
        self._line.swap_characters_before_cursor()

    def ctrl_u(self):
        pass

    def ctrl_v(self):
        pass

    def ctrl_w(self):
        pass

    def ctrl_x(self):
        pass

    def ctrl_y(self):
        # Pastes the clipboard content.
        self._line.insert_text(self._clipboard)

    def ctrl_z(self):
        pass

    def page_up(self):
        self._line.history_backward()

    def page_down(self):
        self._line.history_forward()

    def arrow_left(self):
        self._line.cursor_left()

    def arrow_right(self):
        self._line.cursor_right()

    def arrow_up(self):
        self._line.auto_up()

    def arrow_down(self):
        self._line.auto_down()

    def backspace(self):
        self._line.delete_character_before_cursor()

    def delete(self):
        self._line.delete()

    def tab(self):
        """
        Autocomplete.
        """
        if self._second_tab:
            self._line.list_completions()
            self._second_tab = False
        else:
            self._second_tab = not self._line.complete()

    def insert_char(self, data):
        """ Insert data at cursor position.  """
        assert len(data) == 1

        # Don't create an entry in the history buffer for every single typed
        # character. (Undo should undo multiple typed characters at once.)
        safe = self._last_call != 'insert_char'

        self._line.insert_text(data, safe_current_in_undo_buffer=safe)

    def enter(self):
        self._line.return_input()

    def alt_enter(self): # ESC-enter should always accept. -> enter in VI
                         # insert mode should insert a newline. For emacs not
                         # sure yet.
        self._line.newline()


class EmacsInputStreamHandler(InputStreamHandler):
    """
    Some e-macs extensions.
    """
    def __init__(self, line):
        super(EmacsInputStreamHandler, self).__init__(line)
        self._escape_pressed = False

    def escape(self):
        self._escape_pressed = True

    def __call__(self, name, *a):
        # When escape was pressed, call the `alt_`-function instead.
        # (This is emacs-mode behaviour. The alt-prefix is equal to the escape
        # key, and in VI mode, that's used to go from insert to navigation mode.)
        if self._escape_pressed:
            if name == 'insert_char':
                name = 'alt_' + a[0]
                a = []
            else:
                name = 'alt_' + name
            self._escape_pressed = False

        super(EmacsInputStreamHandler, self).__call__(name, *a)

    def alt_ctrl_j(self):
        """ ALT + Newline """
        # Alias for alt_enter
        self.alt_enter()

    def alt_ctrl_m(self):
        """ ALT + Carriage return """
        # Alias for alt_enter
        self.alt_enter()

    def alt_enter(self):
        pass

    def alt_f(self): # XXX: unittest.
        self._line.cursor_word_forward()

    def alt_b(self):
        self._line.cursor_word_back()

    def alt_d(self):
        """
        Delete the Word after the cursor.
        """

    def ctrl_u(self):
        """
        Clears the line before the cursor position. If you are at the end of
        the line, clears the entire line.
        """
        pass

    def ctrl_w(self):
        """
        Delete the word before the cursor.
        """

    def alt_t(self):
        """
        Swap the last two words before the cursor.
        """

    def ctrl_underscore(self):
        """
        Undo.
        """

    def alt_backslash(self):
        """
        Delete all spaces and tabs around point.
        (delete-horizontal-space)
        """

    def alt_star(self):
        """
        `alt-*`: Insert all possible completions of the preceding text.
        """

    # TODO: ctrl_x, ctrl_e sequence should open an editor. (like 'v' in VI mode.)
    # TODO: ctrl_x, ctrl_u sequence should undo
    # TODO: ctrl_x, ctrl_x move cursor to the start/end again.

            # We can implement these as follows:
            #     if an InputStreamHandler returns a not None value.
            #     that object becomes the new InputStreamHandler


class ViInputStreamHandler(InputStreamHandler):
    """
    Vi extensions.
    """
    def _reset(self):
        super(ViInputStreamHandler, self)._reset()
        self._vi_navigation_mode = False
        self._arg_count = None # Usually for repeats
        self._all_navigation_handles = self._get_navigation_mode_handles()

    def escape(self):
        """ Escape goes to vi navigation mode. """
        self._vi_navigation_mode = True
        self._current_handles = self._all_navigation_handles

        # Reset arg count.
        self._arg_count = None

    def enter(self):
        if self._vi_navigation_mode:
            self._line.return_input()
        else:
            self._line.newline()

    def _get_navigation_mode_handles(self):
        """
        Create a dictionary that maps the vi key binding to their handlers.
        """
        handles = { }
        line = self._line

        def handle(key):
            """ Decorator that registeres the handler function in the handles dict. """
            def wrapper(func):
                handles[key] = func
                return func
            return wrapper

        # List of navigation commands: http://hea-www.harvard.edu/~fine/Tech/vi.html

        @handle('x')
        def _(arg):
            # Delete character.
            self._clipboard = ''.join(line.delete() for i in range(arg))

        @handle('X')
        def _(arg):
            line.delete_character_before_cursor()

        @handle('e')
        @handle('E')
        def _(arg):
            # TODO: end of word
            pass

        @handle('o')
        def _(arg):
            # TODO: open line below and enter insertion mode
            pass

        @handle('r')
        def _(arg):
            # TODO: replace single character under cursor
            pass

        @handle('s')
        def _(arg):
            # TODO: substitute single character with new text
            pass

        @handle('dd')
        def _(arg):
            self._clipboard = ''.join(line.delete_current_line() for i in range(arg))

        @handle('yy')
        def _(arg):
            self._clipboard = line.document.current_line # XXX: we need to keep a
                                       #  state. if we copied a line. it should
                                       #  not be inserted in the middle of
                                       #  another line during a paste.

        @handle('dw')
        def _(arg):
            self._clipboard = ''.join(line.delete_word() for i in range(arg))

        @handle('cw')
        def _(arg):
            self._clipboard = line.delete_word()
            self._vi_navigation_mode = False

        @handle('h')
        def _(arg):
            for i in range(arg):
                line.cursor_left()

        @handle('l')
        @handle(' ')
        def _(arg):
            for i in range(arg):
                line.cursor_right()

        @handle('k')
        def _(arg):
            for i in range(arg):
                line.auto_up()

        @handle('j')
        def _(arg):
            for i in range(arg):
                line.auto_down()

        @handle('H')
        def _(arg):
            # Vi moves to the start of the visible region.
            # cursor position 0 is okay for us.
            line.cursor_position = 0

        @handle('L')
        def _(arg):
            # Vi moves to the start of the visible region.
            # cursor position 0 is okay for us.
            line.cursor_position = len(line.text)

        @handle('i')
        def _(arg):
            self._vi_navigation_mode = False

        @handle('a')
        def _(arg):
            self._vi_navigation_mode = False
            line.cursor_right()

        @handle('I')
        def _(arg):
            self._vi_navigation_mode = False
            line.cursor_to_start_of_line()

        @handle('J')
        def _(arg):
            line.join_next_line()

        @handle('p')
        def _(arg):
            for i in range(arg):
                line.insert_text(self._clipboard)

        @handle('A')
        def _(arg):
            self._vi_navigation_mode = False
            line.cursor_to_end_of_line()

        @handle('C')
        def _(arg):
            # Change to end of line.
            self._clipboard = line.delete_until_end_of_line()
            self._vi_navigation_mode = False

        @handle('D')
        def _(arg):
            self._clipboard = line.delete_until_end_of_line()

        @handle('b')
        def _(arg):
            for i in range(arg):
                line.cursor_word_back()

        @handle('w')
        def _(arg):
            for i in range(arg):
                line.cursor_word_forward()

        @handle('v')
        def _(arg):
            line.open_in_editor()

        @handle('^')
        def _(arg):
            line.cursor_to_start_of_line(after_whitespace=True)

        @handle('$')
        def _(arg):
            # TODO: This should not move after but *on* the last character.
            line.cursor_to_end_of_line()

        @handle('%')
        def _(arg):
            # Match nearest [], (), {} on line, to its match.
            line.go_to_matching_bracket()

        @handle('u')
        def _(arg):
            for i in range(arg):
                line.undo()

        @handle('+')
        def _(arg):
            # TODO: move to first non whitespace of next line
            pass

        @handle('-')
        def _(arg):
            # TODO: move to first non whitespace of previous line
            pass

        @handle('{')
        def _(arg):
            # TODO: Move to previous blank-line separated section.
            #while not line.current_line.isspace():
            #    line.cursor_up()
            pass

        @handle('}')
        def _(arg):
            # TODO: move to next blank-line separated section.
            pass

        @handle('>>')
        def _(arg):
            # TODO: Indent current line.
            pass

        @handle('<<')
        def _(arg):
            # TODO: Unindent current line.
            pass

        @handle('~')
        def _(arg):
            """ Reverse case of current character and move cursor forward. """
            c = line.document.current_char
            if c is not None:
                c = (c.upper() if c.islower() else c.lower())
                line.insert_text(c, overwrite=True)

        return handles

    def __call__(self, name, *a):
        super(ViInputStreamHandler, self).__call__(name, *a)

        # Set argument prompt
        if self._arg_count:
            self._line.set_arg_prompt(self._arg_count)
        else:
            self._line.set_arg_prompt('')

    def insert_char(self, data):
        """ Insert data at cursor position.  """
        assert len(data) == 1

        if self._vi_navigation_mode:
            # Always handle numberics to build the arg
            if data in '0123456789':
                if self._arg_count is None:
                    self._arg_count = int(data)
                else:
                    self._arg_count = int("%s%s" % (self._arg_count, data))

                # Don't exceed a million.
                if int(self._arg_count) >= 1000000:
                    self._arg_count = None

            # If we have a handle for the current keypress. Call it.
            elif data in self._current_handles:
                # Pass argument to handle.
                arg_count = self._arg_count
                self._arg_count = None

                self._current_handles[data](arg_count or 1)
                self._current_handles = self._all_navigation_handles

            # If there are several combitations of handles, starting with the
            # keys that were already pressed. Reduce to this subset of
            # handlers.
            elif data in [ k[0] for k in self._current_handles.keys() ]:
                self._current_handles = { k[1:]:h for k, h in self._current_handles.items() if k[0] == data }

            # No match. Reset.
            else:
                self._current_handles = self._all_navigation_handles

        # In insert/text mode.
        else:
            super(ViInputStreamHandler, self).insert_char(data)
