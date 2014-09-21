"""

::

    from prompt_toolkit.contrib.python_import import PythonCommandLineInterface

    cli = PythonCommandLineInterface()
    cli.read_input()
"""
from __future__ import unicode_literals

from pygments.lexers import PythonLexer
from pygments.style import Style
from pygments.token import Keyword, Operator, Number, Name, Error, Comment, Token

from prompt_toolkit import CommandLineInterface
from prompt_toolkit.code import Completion, Code, ValidationError
from prompt_toolkit.enums import InputMode
from prompt_toolkit.history import FileHistory, History
from prompt_toolkit.key_bindings.emacs import emacs_bindings
from prompt_toolkit.key_bindings.vi import vi_bindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.line import Line
from prompt_toolkit.prompt import Prompt, TokenList, BracketsMismatchProcessor, PopupCompletionMenu, HorizontalCompletionMenu
from prompt_toolkit.renderer import Char, Screen, Point
from prompt_toolkit.selection import SelectionType

import jedi
import platform
import re
import sys


__all__ = (
    'PythonCommandLineInterface',
    'AutoCompletionStyle',
)


class AutoCompletionStyle:
    #: tab/double-tab completion
    # TRADITIONAL = 'traditional'  # TODO: not implemented yet.

    #: Pop-up
    POPUP_MENU = 'popup-menu'

    #: Horizontal list
    HORIZONTAL_MENU = 'horizontal-menu'

    #: No visualisation
    NONE = 'none'


class PythonStyle(Style):
    background_color = None
    styles = {
        Keyword:                       '#ee00ee',
        Operator:                      '#ff6666 bold',
        Number:                        '#ff0000',
        Name:                          '#008800',
        Name.Namespace:                '#008800 underline',
        Name.Decorator:                '#aa22ff',

        Token.Literal.String:          '#ba4444 bold',

        Error:                         '#000000 bg:#ff8888',
        Comment:                       '#0000dd',
        Token.Bash:                    '#333333',
        Token.IPython:                 '#660066',

        Token.IncrementalSearchMatch:         '#ffffff bg:#4444aa',
        Token.IncrementalSearchMatch.Current: '#ffffff bg:#44aa44',

        Token.SelectedText:            '#ffffff bg:#6666aa',

        # Signature highlighting.
        Token.Signature:               '#888888',
        Token.Signature.Operator:      'bold #888888',
        Token.Signature.CurrentName:   'bold underline #888888',

        # Highlighting for the reverse-search prompt.
        Token.Prompt:                     'bold #008800',
        Token.Prompt.ISearch:             'noinherit',
        Token.Prompt.ISearch.Text:        'bold',
        Token.Prompt.ISearch.Text.NoMatch: 'bg:#aa4444 #ffffff',

        Token.Prompt.SecondLinePrefix: 'bold #888888',
        Token.Prompt.LineNumber:       '#aa6666',
        Token.Prompt.Arg:              'noinherit',
        Token.Prompt.Arg.Text:          'bold',

        Token.Toolbar:                 'bg:#222222 #aaaaaa',
        Token.Toolbar.Off:             'bg:#222222 #888888',
        Token.Toolbar.On:              'bg:#222222 #ffffff',
        Token.Toolbar.Mode:            'bg:#222222 #ffffaa',
        Token.Toolbar.PythonVersion:   'bg:#222222 #ffffff bold',

        # Completion menu
        Token.CompletionMenu.Completion:             'bg:#888888 #ffffbb',
        Token.CompletionMenu.Completion.Current:     'bg:#dddddd #000000',
        Token.CompletionMenu.Meta.Current:           'bg:#bbbbbb #000000',
        Token.CompletionMenu.Meta:                   'bg:#888888 #cccccc',
        Token.CompletionMenu.ProgressBar:            'bg:#aaaaaa',
        Token.CompletionMenu.ProgressButton:         'bg:#000000',

        Token.HorizontalMenu.Completion:              '#888888 noinherit',
        Token.HorizontalMenu.Completion.Current:      'bold',
        Token.HorizontalMenu:                         'noinherit',
        Token.HorizontalMenu.Arrow:                   'bold #888888',

        # Grayed
        Token.Aborted:                 '#888888',

        Token.ValidationError:         'bg:#aa0000 #ffffff',

        # Vi tildes
        Token.Leftmargin.Tilde:   '#888888',
    }


def _has_unclosed_brackets(text):
    """
    Starting at the end of the string. If we find an opening bracket
    for which we didn't had a closing one yet, return True.
    """
    stack = []

    # Ignore braces inside strings
    text = re.sub(r'''('[^']*'|"[^"]*")''', '', text)  # XXX: handle escaped quotes.!

    for c in reversed(text):
        if c in '])}':
            stack.append(c)

        elif c in '[({':
            if stack:
                if ((c == '[' and stack[-1] == ']') or
                        (c == '{' and stack[-1] == '}') or
                        (c == '(' and stack[-1] == ')')):
                    stack.pop()
            else:
                # Opening bracket for which we didn't had a closing one.
                return True

    return False


def python_bindings(registry, cli_ref):
    """
    Custom key bindings.
    """
    line = cli_ref().line
    handle = registry.add_binding

    @handle(Keys.F6)
    def _(event):
        """
        Enable/Disable paste mode.
        """
        line.paste_mode = not line.paste_mode
        if line.paste_mode:
            line.is_multiline = True

    if not cli_ref().always_multiline:
        @handle(Keys.F7)
        def _(event):
            """
            Enable/Disable multiline mode.
            """
            line.is_multiline = not line.is_multiline

    @handle(Keys.Tab, in_mode=InputMode.INSERT)
    @handle(Keys.Tab, in_mode=InputMode.COMPLETE)
    def _(event):
        """
        When the 'tab' key is pressed with only whitespace character before the
        cursor, do autocompletion. Otherwise, insert indentation.
        """
        current_char = line.document.current_line_before_cursor
        if not current_char or current_char.isspace():
            line.insert_text('    ')
        else:
            line.complete_next()
            if event.input_processor.input_mode != InputMode.COMPLETE:
                event.input_processor.push_input_mode(InputMode.COMPLETE)

    @handle(Keys.BackTab, in_mode=InputMode.INSERT)
    @handle(Keys.BackTab, in_mode=InputMode.COMPLETE)
    def _(event):
        """
        Shift+Tab: go to previous completion.
        """
        line.complete_previous()

        if event.input_processor.input_mode != InputMode.COMPLETE:
            event.input_processor.push_input_mode(InputMode.COMPLETE)
            line.complete_previous()


class PythonLine(Line):
    """
    Custom `Line` class with some helper functions.
    """
    tempfile_suffix = '.py'

    def __init__(self, always_multiline, *a, **kw):
        self.always_multiline = always_multiline
        super(PythonLine, self).__init__(*a, **kw)

    def reset(self, *a, **kw):
        super(PythonLine, self).reset(*a, **kw)

        #: Boolean `paste` flag. If True, don't insert whitespace after a
        #: newline.
        self.paste_mode = False

        #: Boolean `multiline` flag. If True, [Enter] will always insert a
        #: newline, and it is required to use [Meta+Enter] execute commands.
        self.is_multiline = self.always_multiline

        # Code signatures. (This is set asynchronously after a timeout.)
        self.signatures = []

    def text_changed(self):
        # When there is '\n' in the input, or in case of paste mode, always
        # make sure that we enable multiline.
        self.is_multiline = '\n' in self.text or self.paste_mode or self.always_multiline

    def newline(self):
        r"""
        Insert \n at the cursor position. Also add necessary padding.
        """
        insert_text = super(PythonLine, self).insert_text

        if self.paste_mode or self.document.current_line_after_cursor:
            insert_text('\n')
        else:
            # Go to new line, but also add indentation.
            current_line = self.document.current_line_before_cursor.rstrip()
            insert_text('\n')

            # Copy whitespace from current line
            for c in current_line:
                if c.isspace():
                    insert_text(c)
                else:
                    break

            # If the last line ends with a colon, add four extra spaces.
            if current_line[-1:] == ':':
                for x in range(4):
                    insert_text(' ')

    def auto_enter(self):
        self._auto_enable_multiline()
        super(PythonLine, self).auto_enter()

    def _auto_enable_multiline(self):
        """
        (Temporarily) enable multiline when pressing enter.
        When:
        - We press [enter] after a color or backslash (line continuation).
        - After unclosed brackets.
        """
        def is_empty_or_space(s):
            return s == '' or s.isspace()
        cursor_at_the_end = self.document.is_cursor_at_the_end

        # If we just typed a colon, or still have open brackets, always insert a real newline.
        if cursor_at_the_end and (self.document.text_before_cursor.rstrip()[-1:] == ':' or
                                  _has_unclosed_brackets(self.document.text_before_cursor) or
                                  self.text.startswith('@')):
            self.is_multiline = True

        # If the character before the cursor is a backslash (line continuation
        # char), insert a new line.
        elif cursor_at_the_end and (self.document.text_before_cursor[-1:] == '\\'):
            self.is_multiline = True

    def complete_after_insert_text(self):
        """
        Start autocompletion when a we have a valid identifier before the
        cursor. (In this case it's not required to press [Tab] in order to view
        the completion menu.)
        """
        word_before_cursor = self.document.get_word_before_cursor()
        return word_before_cursor is not None and word_before_cursor.isidentifier()


class PythonPrompt(Prompt):
    input_processors = [BracketsMismatchProcessor()]

    min_height = 7

    def __init__(self, commandline_ref):
        super(PythonPrompt, self).__init__(commandline_ref)

    def reset(self):
        #: Vertical scrolling position of the main content.
        self.vertical_scroll = 0

    @property
    def completion_menu(self):
        style = self.commandline.autocompletion_style

        if style == AutoCompletionStyle.POPUP_MENU:
            return PopupCompletionMenu()
        elif style == AutoCompletionStyle.HORIZONTAL_MENU:
            return None

    def write_second_toolbar(self, screen):
        """
        When inside functions, show signature.
        """
        if self.commandline.input_processor.input_mode == InputMode.VI_SEARCH:
            self.write_vi_search(screen)

        elif self.commandline.input_processor.input_mode == InputMode.INCREMENTAL_SEARCH and self.line.isearch_state:
            screen.write_highlighted(list(self.isearch_prompt))

        elif self.commandline.input_processor.arg is not None:
            screen.write_highlighted(list(self.arg_prompt))

        elif self.line.validation_error:
            screen.write_highlighted(list(self._get_error_tokens()))

        elif self.commandline.autocompletion_style == AutoCompletionStyle.HORIZONTAL_MENU and \
                self.line.complete_state and \
                self.commandline.input_processor.input_mode == InputMode.COMPLETE:
            HorizontalCompletionMenu().write(screen, None, self.line.complete_state)
        else:
            screen.write_highlighted(list(self._get_signature_tokens()))

    def _get_signature_tokens(self):
        result = []
        append = result.append
        Signature = Token.Signature

        if self.line.signatures:
            sig = self.line.signatures[0]  # Always take the first one.

            append((Token, '           '))
            append((Signature, sig.full_name))
            append((Signature.Operator, '('))

            for i, p in enumerate(sig.params):
                if i == sig.index:
                    append((Signature.CurrentName, str(p.name)))
                else:
                    append((Signature, str(p.name)))
                append((Signature.Operator, ', '))

            result.pop()  # Pop last comma
            append((Signature.Operator, ')'))
        return result

    def _get_error_tokens(self):
        if self.line.validation_error:
            text = '%s (line=%s column=%s)' % (
                self.line.validation_error.message,
                self.line.validation_error.line + 1,
                self.line.validation_error.column + 1)
            return [(Token.ValidationError, text)]
        else:
            return []

    @property
    def prompt_text(self):
        return 'In [%s]: ' % self.commandline.current_statement_index

    def write_prompt(self, screen):
        screen.write_highlighted_at_pos(0, 0, [(Token.Prompt, self.prompt_text)])

    def create_left_input_margin(self, screen, row, is_new_line):
        if is_new_line:
            text = '%i. ' % row
        else:
            text = ''

        screen.write_highlighted([
            (Token.Prompt.LineNumber, ' ' * (len(self.prompt_text) - len(text))),
            (Token.Prompt.LineNumber, text),
        ])

    def write_input_scrolled(self, screen, accept_or_abort, last_screen_height):
        # Write to a temp screen first.
        temp_screen = Screen(screen.size)
        super(PythonPrompt, self).write_input(temp_screen, highlight=not accept_or_abort)

        # Determine the maximum height.
        max_height = screen.size.rows - 2

        if True:
            # Scroll back if we scrolled to much and there's still space at the top.
            if self.vertical_scroll > temp_screen.current_height - max_height:
                self.vertical_scroll = max(0, temp_screen.current_height - max_height)

            # Scroll up if cursor is before visible part.
            if self.vertical_scroll > temp_screen.cursor_position.y:
                self.vertical_scroll = temp_screen.cursor_position.y

            # Scroll down if cursor is after visible part.
            if self.vertical_scroll <= temp_screen.cursor_position.y - max_height:
                self.vertical_scroll = (temp_screen.cursor_position.y + 1) - max_height

            # Scroll down if we need space for the menu.
            if self.need_to_show_completion_menu():
                menu_size = min(5, len(self.line.complete_state.current_completions)) - 1
                if temp_screen.cursor_position.y - self.vertical_scroll >= max_height - menu_size:
                    self.vertical_scroll = (temp_screen.cursor_position.y + 1) - (max_height - menu_size)

        # Now copy the region we need to the real screen.
        y = 0
        for y in range(0, min(max_height, temp_screen.current_height - self.vertical_scroll)):
            for x in range(0, temp_screen.size.columns):
                screen._buffer[y][x] = temp_screen._buffer[y + self.vertical_scroll][x]

        screen.cursor_position = Point(y=temp_screen.cursor_position.y - self.vertical_scroll,
                                       x=temp_screen.cursor_position.x)

        # Fill up with tildes.
        if not accept_or_abort:
            y += 1
            while y < max([self.min_height - 2, last_screen_height - 2]) and y < max_height:
                screen.write_at_pos(y, 1, Char('~', Token.Leftmargin.Tilde))
                y += 1

        return_y = y

        # Show completion menu.
        if not accept_or_abort and self.need_to_show_completion_menu():
            y, x = temp_screen._cursor_mappings[self.line.complete_state.original_document.cursor_position]
            self.completion_menu.write(screen, (y - self.vertical_scroll, x), self.line.complete_state)

        return return_y

    def write_to_screen(self, screen, last_screen_height, accept=False, abort=False):
        y = self.write_input_scrolled(screen, (accept or abort), last_screen_height)
        self.write_prompt(screen)

        if not (accept or abort):
            screen._y, screen._x = y, 0
            self.write_second_toolbar(screen)

            screen._y, screen._x = y + 1, 0
            self.write_toolbar(screen)

    def write_toolbar(self, screen):
        TB = Token.Toolbar
        mode = self.commandline.input_processor.input_mode

        result = TokenList()
        append = result.append

        append((TB, ' '))

        # Mode
        if mode == InputMode.INCREMENTAL_SEARCH:
            append((TB.Mode, '(SEARCH)'))
            append((TB, '   '))
        elif self.commandline.vi_mode:
            if mode == InputMode.INSERT:
                append((TB.Mode, '(INSERT)'))
                append((TB, '   '))
            elif mode == InputMode.VI_SEARCH:
                append((TB.Mode, '(SEARCH)'))
                append((TB, '   '))
            elif mode == InputMode.VI_NAVIGATION:
                append((TB.Mode, '(NAV)'))
                append((TB, '      '))
            elif mode == InputMode.VI_REPLACE:
                append((TB.Mode, '(REPLACE)'))
                append((TB, '  '))
            elif mode == InputMode.COMPLETE:
                append((TB.Mode, '(COMPLETE)'))
                append((TB, ' '))
            elif mode == InputMode.SELECTION and self.line.selection_state:
                if self.line.selection_state.type == SelectionType.LINES:
                    append((TB.Mode, '(VISUAL LINE)'))
                    append((TB, ' '))
                elif self.line.selection_state.type == SelectionType.CHARACTERS:
                    append((TB.Mode, '(VISUAL)'))
                    append((TB, ' '))

        else:
            append((TB.Mode, '(emacs)'))
            append((TB, ' '))

        # Position in history.
        append((TB, '%i/%i ' % (self.line.working_index + 1, len(self.line._working_lines))))

        # Shortcuts.
        if mode == InputMode.INCREMENTAL_SEARCH:
            append((TB, '[Ctrl-G] Cancel search [Enter] Go to this position.'))
        elif mode == InputMode.SELECTION and not self.commandline.vi_mode:
            # Emacs cut/copy keys.
            append((TB, '[Ctrl-W] Cut [Meta-W] Copy [Ctrl-Y] Paste [Ctrl-G] Cancel'))
        else:
            if self.line.paste_mode:
                append((TB.On, '[F6] Paste mode (on)  '))
            else:
                append((TB.Off, '[F6] Paste mode (off) '))

            if not self.commandline.always_multiline:
                if self.line.is_multiline:
                    append((TB.On, '[F7] Multiline (on)'))
                else:
                    append((TB.Off, '[F7] Multiline (off)'))

            if self.line.is_multiline:
                append((TB, ' [Meta+Enter] Execute'))

            # Python version
            version = sys.version_info
            append((TB, ' - '))
            append((TB.PythonVersion, '%s %i.%i.%i' % (platform.python_implementation(),
                   version.major, version.minor, version.micro)))

        # Adjust toolbar width.
        if len(result) > screen.size.columns:
            # Trim toolbar
            result = result[:screen.size.columns - 3]
            result.append((TB, ' > '))
        else:
            # Extend toolbar until the page width.
            result.append((TB, ' ' * (screen.size.columns - len(result))))

        screen.write_highlighted(result)


class PythonCode(Code):
    lexer = PythonLexer

    def __init__(self, document, globals, locals):
        self._globals = globals
        self._locals = locals
        super(PythonCode, self).__init__(document)

    def validate(self):
        """ Check input for Python syntax errors. """
        try:
            compile(self.text, '<input>', 'exec')
        except SyntaxError as e:
            # Note, the 'or 1' for offset is required because Python 2.7
            # gives `None` as offset in case of '4=4' as input. (Looks like
            # fixed in Python 3.)
            raise ValidationError(e.lineno - 1, (e.offset or 1) - 1, 'Syntax Error')
        except TypeError as e:
            # e.g. "compile() expected string without null bytes"
            raise ValidationError(0, 0, str(e))

    def _get_jedi_script(self):
        try:
            return jedi.Interpreter(
                self.text,
                column=self.document.cursor_position_col,
                line=self.document.cursor_position_row + 1,
                path='input-text',
                namespaces=[self._locals, self._globals])

        except jedi.common.MultiLevelStopIteration:
            # This happens when the document is just a backslash.
            return None
        except ValueError:
            # Invalid cursor position.
            # ValueError('`column` parameter is not in a valid range.')
            return None

    def get_completions(self):
        """ Ask jedi to complete. """
        script = self._get_jedi_script()

        if script:
            for c in script.completions():
                yield Completion(c.name_with_symbols, len(c.complete) - len(c.name_with_symbols),
                                 display=c.name_with_symbols)


class PythonCommandLineInterface(CommandLineInterface):
    prompt_factory = PythonPrompt

    def line_factory(self, *a, **kw):
        return PythonLine(self.always_multiline, *a, **kw)

    def __init__(self, globals=None, locals=None, vi_mode=False, stdin=None, stdout=None, history_filename=None,
                 style=PythonStyle, autocompletion_style=AutoCompletionStyle.POPUP_MENU, always_multiline=False):

        self.globals = globals or {}
        self.locals = locals or globals
        self.history_filename = history_filename
        self.style = style
        self.autocompletion_style = autocompletion_style
        self.always_multiline = always_multiline

        self.vi_mode = vi_mode
        self.get_signatures_thread_running = False

        #: Incremeting integer counting the current statement.
        self.current_statement_index = 1

        super(PythonCommandLineInterface, self).__init__(stdin=stdin, stdout=stdout)

    def history_factory(self):
        if self.history_filename:
            return FileHistory(self.history_filename)
        else:
            return History()

    @property
    def key_bindings_factories(self):
        if self.vi_mode:
            return [vi_bindings, python_bindings]
        else:
            return [emacs_bindings, python_bindings]

    def code_factory(self, document):
        # The `PythonCode` needs a reference back to this class in order to do
        # autocompletion on the globals/locals.
        return PythonCode(document, self.globals, self.locals)

    def on_input_timeout(self):
        """
        When there is no input activity,
        in another thread, get the signature of the current code.
        """
        # Never run multiple get-signature threads.
        if self.get_signatures_thread_running:
            return
        self.get_signatures_thread_running = True

        code = self.line.create_code()

        def run():
            script = code._get_jedi_script()

            # Show signatures in help text.
            if script:
                try:
                    signatures = script.call_signatures()
                except ValueError:
                    # e.g. in case of an invalid \x escape.
                    signatures = []
                except Exception:
                    # Sometimes we still get an exception (TypeError), because
                    # of probably bugs in jedi. We can silence them.
                    signatures = []
            else:
                signatures = []

            self.get_signatures_thread_running = False

            # Set signatures and redraw if the text didn't change in the
            # meantime. Otherwise request new signatures.
            if self.line.text == code.text:
                self.line.signatures = signatures
                self.request_redraw()
            else:
                self.on_input_timeout()

        self.run_in_executor(run)
