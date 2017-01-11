"""
Filters that accept a `Application` as argument.
"""
from __future__ import unicode_literals
from .base import Filter
from prompt_toolkit.cache import memoized
from prompt_toolkit.enums import EditingMode
import six

__all__ = (
    'HasArg',
    'HasCompletions',
    'HasFocus',
    'HasSelection',
    'HasValidationError',
    'IsAborting',
    'IsDone',
#    'IsMultiline',
    'IsReadOnly',
    'RendererHeightIsKnown',
    'InEditingMode',
    'InPasteMode',

    # Vi modes.
    'ViMode',
    'ViNavigationMode',
    'ViInsertMode',
    'ViInsertMultipleMode',
    'ViReplaceMode',
    'ViSelectionMode',
    'ViWaitingForTextObjectMode',
    'ViDigraphMode',

    # Emacs modes.
    'EmacsMode',
    'EmacsInsertMode',
    'EmacsSelectionMode',

    # Searching
    'IsSearching',
    'ControlIsSearchable',
)


@memoized()
class HasFocus(Filter):
    """
    Enable when this buffer has the focus.
    """
    def __init__(self, value):
        from prompt_toolkit.buffer import Buffer
        from prompt_toolkit.layout.controls import UIControl
        assert isinstance(value, (six.text_type, Buffer, UIControl)), value
        self.value = value

        if isinstance(value, six.text_type):
            def test(app):
                return app.current_buffer.name == value
        elif isinstance(value, Buffer):
            def test(app):
                return app.current_buffer == value
        elif isinstance(value, UIControl):
            def test(app):
                return app.focussed_control == value

        self._test = test

    def __call__(self, app):
        return self._test(app)

    def __repr__(self):
        return 'HasFocus(%r)' % self.value


@memoized()
class HasSelection(Filter):
    """
    Enable when the current buffer has a selection.
    """
    def __call__(self, app):
        return bool(app.current_buffer.selection_state)

    def __repr__(self):
        return 'HasSelection()'


@memoized()
class HasCompletions(Filter):
    """
    Enable when the current buffer has completions.
    """
    def __call__(self, app):
        return app.current_buffer.complete_state is not None

    def __repr__(self):
        return 'HasCompletions()'


#@memoized()
#class IsMultiline(Filter):
#    """
#    Enable in multiline mode.
#    """
#    def __call__(self, app):
#        return app.current_buffer.is_multiline()
#
#    def __repr__(self):
#        return 'IsMultiline()'


@memoized()
class IsReadOnly(Filter):
    """
    True when the current buffer is read only.
    """
    def __call__(self, app):
        return app.current_buffer.read_only()

    def __repr__(self):
        return 'IsReadOnly()'


@memoized()
class HasValidationError(Filter):
    """
    Current buffer has validation error.
    """
    def __call__(self, app):
        return app.current_buffer.validation_error is not None

    def __repr__(self):
        return 'HasValidationError()'


@memoized()
class HasArg(Filter):
    """
    Enable when the input processor has an 'arg'.
    """
    def __call__(self, app):
        return app.key_processor.arg is not None

    def __repr__(self):
        return 'HasArg()'


@memoized()
class IsAborting(Filter):
    """
    True when aborting. (E.g. Control-C pressed.)
    """
    def __call__(self, app):
        return app.is_aborting

    def __repr__(self):
        return 'IsAborting()'


@memoized()
class IsExiting(Filter):
    """
    True when exiting. (E.g. Control-D pressed.)
    """
    def __call__(self, app):
        return app.is_exiting

    def __repr__(self):
        return 'IsExiting()'


@memoized()
class IsDone(Filter):
    """
    True when the CLI is returning, aborting or exiting.
    """
    def __call__(self, app):
        return app.is_done

    def __repr__(self):
        return 'IsDone()'


@memoized()
class RendererHeightIsKnown(Filter):
    """
    Only True when the renderer knows it's real height.

    (On VT100 terminals, we have to wait for a CPR response, before we can be
    sure of the available height between the cursor position and the bottom of
    the terminal. And usually it's nicer to wait with drawing bottom toolbars
    until we receive the height, in order to avoid flickering -- first drawing
    somewhere in the middle, and then again at the bottom.)
    """
    def __call__(self, app):
        return app.renderer.height_is_known

    def __repr__(self):
        return 'RendererHeightIsKnown()'


@memoized()
class InEditingMode(Filter):
    """
    Check whether a given editing mode is active. (Vi or Emacs.)
    """
    def __init__(self, editing_mode):
        self._editing_mode = editing_mode

    @property
    def editing_mode(self):
        " The given editing mode. (Read-only) "
        return self._editing_mode

    def __call__(self, app):
        return app.editing_mode == self.editing_mode

    def __repr__(self):
        return 'InEditingMode(%r)' % (self.editing_mode, )


@memoized()
class InPasteMode(Filter):
    def __call__(self, app):
        return app.paste_mode(app)


@memoized()
class ViMode(Filter):
    def __call__(self, app):
        return app.editing_mode == EditingMode.VI

    def __repr__(self):
        return 'ViMode()'


@memoized()
class ViNavigationMode(Filter):
    """
    Active when the set for Vi navigation key bindings are active.
    """
    def __call__(self, app):
        from prompt_toolkit.key_binding.vi_state import InputMode
        if (app.editing_mode != EditingMode.VI
                or app.vi_state.operator_func
                or app.vi_state.waiting_for_digraph
                or app.current_buffer.selection_state):
            return False

        return (app.vi_state.input_mode == InputMode.NAVIGATION or
                app.current_buffer.read_only())

    def __repr__(self):
        return 'ViNavigationMode()'


@memoized()
class ViInsertMode(Filter):
    def __call__(self, app):
        from prompt_toolkit.key_binding.vi_state import InputMode
        if (app.editing_mode != EditingMode.VI
                or app.vi_state.operator_func
                or app.vi_state.waiting_for_digraph
                or app.current_buffer.selection_state
                or app.current_buffer.read_only()):
            return False

        return app.vi_state.input_mode == InputMode.INSERT

    def __repr__(self):
        return 'ViInsertMode()'


@memoized()
class ViInsertMultipleMode(Filter):
    def __call__(self, app):
        from prompt_toolkit.key_binding.vi_state import InputMode
        if (app.editing_mode != EditingMode.VI
                or app.vi_state.operator_func
                or app.vi_state.waiting_for_digraph
                or app.current_buffer.selection_state
                or app.current_buffer.read_only()):
            return False

        return app.vi_state.input_mode == InputMode.INSERT_MULTIPLE

    def __repr__(self):
        return 'ViInsertMultipleMode()'


@memoized()
class ViReplaceMode(Filter):
    def __call__(self, app):
        from prompt_toolkit.key_binding.vi_state import InputMode
        if (app.editing_mode != EditingMode.VI
                or app.vi_state.operator_func
                or app.vi_state.waiting_for_digraph
                or app.current_buffer.selection_state
                or app.current_buffer.read_only()):
            return False

        return app.vi_state.input_mode == InputMode.REPLACE

    def __repr__(self):
        return 'ViReplaceMode()'


@memoized()
class ViSelectionMode(Filter):
    def __call__(self, app):
        if app.editing_mode != EditingMode.VI:
            return False

        return bool(app.current_buffer.selection_state)

    def __repr__(self):
        return 'ViSelectionMode()'


@memoized()
class ViWaitingForTextObjectMode(Filter):
    def __call__(self, app):
        if app.editing_mode != EditingMode.VI:
            return False

        return app.vi_state.operator_func is not None

    def __repr__(self):
        return 'ViWaitingForTextObjectMode()'


@memoized()
class ViDigraphMode(Filter):
    def __call__(self, app):
        if app.editing_mode != EditingMode.VI:
            return False

        return app.vi_state.waiting_for_digraph

    def __repr__(self):
        return 'ViDigraphMode()'


@memoized()
class EmacsMode(Filter):
    " When the Emacs bindings are active. "
    def __call__(self, app):
        return app.editing_mode == EditingMode.EMACS

    def __repr__(self):
        return 'EmacsMode()'


@memoized()
class EmacsInsertMode(Filter):
    def __call__(self, app):
        if (app.editing_mode != EditingMode.EMACS
                or app.current_buffer.selection_state
                or app.current_buffer.read_only()):
            return False
        return True

    def __repr__(self):
        return 'EmacsInsertMode()'


@memoized()
class EmacsSelectionMode(Filter):
    def __call__(self, app):
        return (app.editing_mode == EditingMode.EMACS
                and app.current_buffer.selection_state)

    def __repr__(self):
        return 'EmacsSelectionMode()'


@memoized()
class IsSearching(Filter):
    " When we are searching. "
    def __call__(self, app):
        from prompt_toolkit.layout.controls import BufferControl
        control = app.focus.focussed_control
        prev = app.focus.previous_focussed_control

        return (isinstance(prev, BufferControl) and
                isinstance(control, BufferControl) and
                prev.search_buffer_control is not None and
                prev.search_buffer_control == control)

    def __repr__(self):
        return 'IsSearching()'


@memoized()
class ControlIsSearchable(Filter):
    " When the current UIControl is searchable. "
    def __call__(self, app):
        from prompt_toolkit.layout.controls import BufferControl
        control = app.focussed_control

        return (isinstance(control, BufferControl) and
                control.search_buffer_control is not None)

    def __repr__(self):
        return 'ControlIsSearchable()'


# For backwards compatibility.
HasSearch = IsSearching
