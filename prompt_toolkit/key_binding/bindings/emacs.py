# pylint: disable=function-redefined
from __future__ import unicode_literals
from prompt_toolkit.buffer import SelectionType, indent, unindent
from prompt_toolkit.keys import Keys
from prompt_toolkit.enums import SearchDirection
from prompt_toolkit.filters import Condition, EmacsMode, HasSelection, EmacsInsertMode, HasFocus, HasArg, IsSearching, ControlIsSearchable
from prompt_toolkit.completion import CompleteEvent

from .scroll import scroll_page_up, scroll_page_down
from .named_commands import get_by_name
from ..registry import Registry, ConditionalRegistry

__all__ = (
    'load_emacs_bindings',
    'load_emacs_search_bindings',
    'load_extra_emacs_page_navigation_bindings',
)


def load_emacs_bindings():
    """
    Some e-macs extensions.
    """
    # Overview of Readline emacs commands:
    # http://www.catonmat.net/download/readline-emacs-editing-mode-cheat-sheet.pdf
    registry = Registry()
    handle = registry.add_binding

    insert_mode = EmacsInsertMode()
    has_selection = HasSelection()

    @handle(Keys.Escape)
    def _(event):
        """
        By default, ignore escape key.

        (If we don't put this here, and Esc is followed by a key which sequence
        is not handled, we'll insert an Escape character in the input stream.
        Something we don't want and happens to easily in emacs mode.
        Further, people can always use ControlQ to do a quoted insert.)
        """
        pass

    handle(Keys.ControlA)(get_by_name('beginning-of-line'))
    handle(Keys.ControlB)(get_by_name('backward-char'))
    handle(Keys.ControlDelete, filter=insert_mode)(get_by_name('kill-word'))
    handle(Keys.ControlE)(get_by_name('end-of-line'))
    handle(Keys.ControlF)(get_by_name('forward-char'))
    handle(Keys.ControlLeft)(get_by_name('backward-word'))
    handle(Keys.ControlRight)(get_by_name('forward-word'))
    handle(Keys.ControlX, 'r', 'y', filter=insert_mode)(get_by_name('yank'))
    handle(Keys.ControlY, filter=insert_mode)(get_by_name('yank'))
    handle(Keys.Escape, 'b')(get_by_name('backward-word'))
    handle(Keys.Escape, 'c', filter=insert_mode)(get_by_name('capitalize-word'))
    handle(Keys.Escape, 'd', filter=insert_mode)(get_by_name('kill-word'))
    handle(Keys.Escape, 'f')(get_by_name('forward-word'))
    handle(Keys.Escape, 'l', filter=insert_mode)(get_by_name('downcase-word'))
    handle(Keys.Escape, 'u', filter=insert_mode)(get_by_name('uppercase-word'))
    handle(Keys.Escape, 'y', filter=insert_mode)(get_by_name('yank-pop'))
    handle(Keys.Escape, Keys.ControlH, filter=insert_mode)(get_by_name('backward-kill-word'))
    handle(Keys.Escape, Keys.Backspace, filter=insert_mode)(get_by_name('backward-kill-word'))
    handle(Keys.Escape, '\\', filter=insert_mode)(get_by_name('delete-horizontal-space'))

    handle(Keys.ControlUnderscore, save_before=(lambda e: False), filter=insert_mode)(
        get_by_name('undo'))

    handle(Keys.ControlX, Keys.ControlU, save_before=(lambda e: False), filter=insert_mode)(
        get_by_name('undo'))


    handle(Keys.Escape, '<', filter= ~has_selection)(get_by_name('beginning-of-history'))
    handle(Keys.Escape, '>', filter= ~has_selection)(get_by_name('end-of-history'))

    handle(Keys.Escape, '.', filter=insert_mode)(get_by_name('yank-last-arg'))
    handle(Keys.Escape, '_', filter=insert_mode)(get_by_name('yank-last-arg'))
    handle(Keys.Escape, Keys.ControlY, filter=insert_mode)(get_by_name('yank-nth-arg'))
    handle(Keys.Escape, '#', filter=insert_mode)(get_by_name('insert-comment'))
    handle(Keys.ControlO)(get_by_name('operate-and-get-next'))

    # ControlQ does a quoted insert. Not that for vt100 terminals, you have to
    # disable flow control by running ``stty -ixon``, otherwise Ctrl-Q and
    # Ctrl-S are captured by the terminal.
    handle(Keys.ControlQ, filter= ~has_selection)(get_by_name('quoted-insert'))

    handle(Keys.ControlX, '(')(get_by_name('start-kbd-macro'))
    handle(Keys.ControlX, ')')(get_by_name('end-kbd-macro'))
    handle(Keys.ControlX, 'e')(get_by_name('call-last-kbd-macro'))

    @handle(Keys.ControlN)
    def _(event):
        " Next line. "
        event.current_buffer.auto_down()

    @handle(Keys.ControlP)
    def _(event):
        " Previous line. "
        event.current_buffer.auto_up(count=event.arg)

    def handle_digit(c):
        """
        Handle input of arguments.
        The first number needs to be preceeded by escape.
        """
        @handle(c, filter=HasArg())
        @handle(Keys.Escape, c)
        def _(event):
            event.append_to_arg_count(c)

    for c in '0123456789':
        handle_digit(c)

    @handle(Keys.Escape, '-', filter=~HasArg())
    def _(event):
        """
        """
        if event._arg is None:
            event.append_to_arg_count('-')

    @handle('-', filter=Condition(lambda app: app.key_processor.arg == '-'))
    def _(event):
        """
        When '-' is typed again, after exactly '-' has been given as an
        argument, ignore this.
        """
        event.app.key_processor.arg = '-'

    is_returnable = Condition(
        lambda app: app.current_buffer.accept_action.is_returnable)

    # Meta + Newline: always accept input.
    handle(Keys.Escape, Keys.Enter, filter=insert_mode & is_returnable)(
        get_by_name('accept-line'))

    def character_search(buff, char, count):
        if count < 0:
            match = buff.document.find_backwards(char, in_current_line=True, count=-count)
        else:
            match = buff.document.find(char, in_current_line=True, count=count)

        if match is not None:
            buff.cursor_position += match

    @handle(Keys.ControlSquareClose, Keys.Any)
    def _(event):
        " When Ctl-] + a character is pressed. go to that character. "
        # Also named 'character-search'
        character_search(event.current_buffer, event.data, event.arg)

    @handle(Keys.Escape, Keys.ControlSquareClose, Keys.Any)
    def _(event):
        " Like Ctl-], but backwards. "
        # Also named 'character-search-backward'
        character_search(event.current_buffer, event.data, -event.arg)

    @handle(Keys.Escape, 'a')
    def _(event):
        " Previous sentence. "
        # TODO:

    @handle(Keys.Escape, 'e')
    def _(event):
        " Move to end of sentence. "
        # TODO:

    @handle(Keys.Escape, 't', filter=insert_mode)
    def _(event):
        """
        Swap the last two words before the cursor.
        """
        # TODO

    @handle(Keys.Escape, '*', filter=insert_mode)
    def _(event):
        """
        `meta-*`: Insert all possible completions of the preceding text.
        """
        buff = event.current_buffer

        # List all completions.
        complete_event = CompleteEvent(text_inserted=False, completion_requested=True)
        completions = list(buff.completer.get_completions(buff.document, complete_event))

        # Insert them.
        text_to_insert = ' '.join(c.text for c in completions)
        buff.insert_text(text_to_insert)

    @handle(Keys.ControlX, Keys.ControlX)
    def _(event):
        """
        Move cursor back and forth between the start and end of the current
        line.
        """
        buffer = event.current_buffer

        if buffer.document.is_cursor_at_the_end_of_line:
            buffer.cursor_position += buffer.document.get_start_of_line_position(after_whitespace=False)
        else:
            buffer.cursor_position += buffer.document.get_end_of_line_position()

    @handle(Keys.ControlSpace)
    def _(event):
        """
        Start of the selection (if the current buffer is not empty).
        """
        # Take the current cursor position as the start of this selection.
        buff = event.current_buffer
        if buff.text:
            buff.start_selection(selection_type=SelectionType.CHARACTERS)

    @handle(Keys.ControlG, filter= ~has_selection)
    def _(event):
        """
        Control + G: Cancel completion menu and validation state.
        """
        event.current_buffer.complete_state = None
        event.current_buffer.validation_error = None

    @handle(Keys.ControlG, filter=has_selection)
    def _(event):
        """
        Cancel selection.
        """
        event.current_buffer.exit_selection()

    @handle(Keys.ControlW, filter=has_selection)
    @handle(Keys.ControlX, 'r', 'k', filter=has_selection)
    def _(event):
        """
        Cut selected text.
        """
        data = event.current_buffer.cut_selection()
        event.app.clipboard.set_data(data)

    @handle(Keys.Escape, 'w', filter=has_selection)
    def _(event):
        """
        Copy selected text.
        """
        data = event.current_buffer.copy_selection()
        event.app.clipboard.set_data(data)

    @handle(Keys.Escape, Keys.Left)
    def _(event):
        """
        Cursor to start of previous word.
        """
        buffer = event.current_buffer
        buffer.cursor_position += buffer.document.find_previous_word_beginning(count=event.arg) or 0

    @handle(Keys.Escape, Keys.Right)
    def _(event):
        """
        Cursor to start of next word.
        """
        buffer = event.current_buffer
        buffer.cursor_position += buffer.document.find_next_word_beginning(count=event.arg) or \
            buffer.document.get_end_of_document_position()

    @handle(Keys.Escape, '/', filter=insert_mode)
    def _(event):
        """
        M-/: Complete.
        """
        b = event.current_buffer
        if b.complete_state:
            b.complete_next()
        else:
            b.start_completion(select_first=True)

    @handle(Keys.ControlC, '>', filter=has_selection)
    def _(event):
        """
        Indent selected text.
        """
        buffer = event.current_buffer

        buffer.cursor_position += buffer.document.get_start_of_line_position(after_whitespace=True)

        from_, to = buffer.document.selection_range()
        from_, _ = buffer.document.translate_index_to_position(from_)
        to, _ = buffer.document.translate_index_to_position(to)

        indent(buffer, from_, to + 1, count=event.arg)

    @handle(Keys.ControlC, '<', filter=has_selection)
    def _(event):
        """
        Unindent selected text.
        """
        buffer = event.current_buffer

        from_, to = buffer.document.selection_range()
        from_, _ = buffer.document.translate_index_to_position(from_)
        to, _ = buffer.document.translate_index_to_position(to)

        unindent(buffer, from_, to + 1, count=event.arg)

    return ConditionalRegistry(registry, EmacsMode())


def load_emacs_open_in_editor_bindings():
    """
    Pressing C-X C-E will open the buffer in an external editor.
    """
    registry = Registry()

    registry.add_binding(Keys.ControlX, Keys.ControlE,
                         filter=EmacsMode() & ~HasSelection())(
         get_by_name('edit-and-execute-command'))

    return registry


def load_emacs_search_bindings():
    registry = Registry()
    handle = registry.add_binding

    is_searching = IsSearching()
    control_is_searchable = ControlIsSearchable()

    @handle(Keys.ControlG, filter=is_searching)
    @handle(Keys.ControlC, filter=is_searching)
    # NOTE: the reason for not also binding Escape to this one, is that we want
    #       Alt+Enter to accept input directly in incremental search mode.
    def _(event):
        """
        Abort an incremental search and restore the original line.
        """
        event.app.current_buffer.reset()
        event.app.focus.focus_previous()

    @handle(Keys.Enter, filter=is_searching)
    def _(event):
        """
        When enter pressed in isearch, quit isearch mode. (Multiline
        isearch would be too complicated.)
        """
        search_control = event.app.focus.focussed_control
        prev_control = event.app.focus.previous_focussed_control
        search_state = prev_control.search_state

        # Update search state.
        if search_control.buffer.text:
            search_state.text = search_control.buffer.text

        # Apply search.
        prev_control.buffer.apply_search(search_state, include_current_position=True)

        # Add query to history of search line.
        search_control.buffer.append_to_history()
        search_control.buffer.reset()

        # Focus previous document again.
        event.app.focus.focus_previous()

    @handle(Keys.ControlR, filter=control_is_searchable)
    def _(event):
        control = event.app.focus.focussed_control
        search_state = control.search_state

        search_state.direction = SearchDirection.BACKWARD
        event.app.focussed_control = control.search_buffer_control

    @handle(Keys.ControlS, filter=control_is_searchable)
    def _(event):
        control = event.app.focus.focussed_control
        search_state = control.search_state

        search_state.direction = SearchDirection.FORWARD
        event.app.focussed_control = control.search_buffer_control

    def incremental_search(app, direction, count=1):
        " Apply search, but keep search buffer focussed. "
        assert is_searching(app)

        search_control = app.focus.focussed_control
        prev_control = app.focus.previous_focussed_control
        search_state = prev_control.search_state

        # Update search_state.
        direction_changed = search_state.direction != direction

        search_state.text = search_control.buffer.text
        search_state.direction = direction

        # Apply search to current buffer.
        if not direction_changed:
            prev_control.buffer.apply_search(
                search_state, include_current_position=False, count=count)

    @handle(Keys.ControlR, filter=is_searching)
    @handle(Keys.Up, filter=is_searching)
    def _(event):
        incremental_search(event.app, SearchDirection.BACKWARD, count=event.arg)

    @handle(Keys.ControlS, filter=is_searching)
    @handle(Keys.Down, filter=is_searching)
    def _(event):
        incremental_search(event.app, SearchDirection.FORWARD, count=event.arg)

    return ConditionalRegistry(registry, EmacsMode())


def load_extra_emacs_page_navigation_bindings():
    """
    Key bindings, for scrolling up and down through pages.
    This are separate bindings, because GNU readline doesn't have them.
    """
    registry = Registry()
    handle = registry.add_binding

    handle(Keys.ControlV)(scroll_page_down)
    handle(Keys.PageDown)(scroll_page_down)
    handle(Keys.Escape, 'v')(scroll_page_up)
    handle(Keys.PageUp)(scroll_page_up)

    return ConditionalRegistry(registry, EmacsMode())
