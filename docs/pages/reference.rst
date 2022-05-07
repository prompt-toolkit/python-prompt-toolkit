Reference
=========

Application
-----------

.. automodule:: prompt_toolkit.application
    :members: Application, get_app, get_app_or_none, set_app,
        create_app_session, AppSession, get_app_session, DummyApplication,
        in_terminal, run_in_terminal,


Formatted text
--------------

.. automodule:: prompt_toolkit.formatted_text
    :members:


Buffer
------

.. automodule:: prompt_toolkit.buffer
    :members:


Selection
---------

.. automodule:: prompt_toolkit.selection
    :members:


Clipboard
---------

.. automodule:: prompt_toolkit.clipboard
    :members: Clipboard, ClipboardData, DummyClipboard, DynamicClipboard, InMemoryClipboard

.. automodule:: prompt_toolkit.clipboard.pyperclip
    :members:


Auto completion
---------------

.. automodule:: prompt_toolkit.completion
    :members:


Document
--------

.. automodule:: prompt_toolkit.document
    :members:


Enums
-----

.. automodule:: prompt_toolkit.enums
    :members:


History
-------

.. automodule:: prompt_toolkit.history
    :members:


Keys
----

.. automodule:: prompt_toolkit.keys
    :members:


Style
-----

.. automodule:: prompt_toolkit.styles
    :members: Attrs, ANSI_COLOR_NAMES, BaseStyle, DummyStyle, DynamicStyle,
        Style, Priority, merge_styles, style_from_pygments_cls,
        style_from_pygments_dict, pygments_token_to_classname, NAMED_COLORS,
        StyleTransformation, SwapLightAndDarkStyleTransformation,
        AdjustBrightnessStyleTransformation, merge_style_transformations,
        DummyStyleTransformation, ConditionalStyleTransformation,
        DynamicStyleTransformation


Shortcuts
---------

.. automodule:: prompt_toolkit.shortcuts
    :members: prompt, PromptSession, confirm, CompleteStyle,
        create_confirm_session, clear, clear_title, print_formatted_text,
        set_title, ProgressBar, input_dialog, message_dialog, progress_dialog,
        radiolist_dialog, yes_no_dialog, button_dialog

.. automodule:: prompt_toolkit.shortcuts.progress_bar.formatters
    :members:


Validation
----------

.. automodule:: prompt_toolkit.validation
    :members:


Auto suggestion
---------------

.. automodule:: prompt_toolkit.auto_suggest
    :members:


Renderer
--------

.. automodule:: prompt_toolkit.renderer
    :members:

Lexers
------

.. automodule:: prompt_toolkit.lexers
    :members:


Layout
------

.. automodule:: prompt_toolkit.layout

The layout class itself
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: prompt_toolkit.layout.Layout
    :members:

.. autoclass:: prompt_toolkit.layout.InvalidLayoutError
    :members:

.. autoclass:: prompt_toolkit.layout.walk
    :members:

Containers
^^^^^^^^^^

.. autoclass:: prompt_toolkit.layout.Container
    :members:

.. autoclass:: prompt_toolkit.layout.HSplit
    :members:

.. autoclass:: prompt_toolkit.layout.VSplit
    :members:

.. autoclass:: prompt_toolkit.layout.FloatContainer
    :members:

.. autoclass:: prompt_toolkit.layout.Float
    :members:

.. autoclass:: prompt_toolkit.layout.Window
    :members:

.. autoclass:: prompt_toolkit.layout.WindowAlign
    :members:

.. autoclass:: prompt_toolkit.layout.ConditionalContainer
    :members:

.. autoclass:: prompt_toolkit.layout.DynamicContainer
    :members:

.. autoclass:: prompt_toolkit.layout.ScrollablePane
    :members:

.. autoclass:: prompt_toolkit.layout.ScrollOffsets
    :members:

.. autoclass:: prompt_toolkit.layout.ColorColumn
    :members:

.. autoclass:: prompt_toolkit.layout.to_container
    :members:

.. autoclass:: prompt_toolkit.layout.to_window
    :members:

.. autoclass:: prompt_toolkit.layout.is_container
    :members:

.. autoclass:: prompt_toolkit.layout.HorizontalAlign
    :members:

.. autoclass:: prompt_toolkit.layout.VerticalAlign
    :members:

Controls
^^^^^^^^

.. autoclass:: prompt_toolkit.layout.BufferControl
    :members:

.. autoclass:: prompt_toolkit.layout.SearchBufferControl
    :members:

.. autoclass:: prompt_toolkit.layout.DummyControl
    :members:

.. autoclass:: prompt_toolkit.layout.FormattedTextControl
    :members:

.. autoclass:: prompt_toolkit.layout.UIControl
    :members:

.. autoclass:: prompt_toolkit.layout.UIContent
    :members:


Other
^^^^^


Sizing
""""""

.. autoclass:: prompt_toolkit.layout.Dimension
    :members:


Margins
"""""""

.. autoclass:: prompt_toolkit.layout.Margin
    :members:

.. autoclass:: prompt_toolkit.layout.NumberedMargin
    :members:

.. autoclass:: prompt_toolkit.layout.ScrollbarMargin
    :members:

.. autoclass:: prompt_toolkit.layout.ConditionalMargin
    :members:

.. autoclass:: prompt_toolkit.layout.PromptMargin
    :members:


Completion Menus
""""""""""""""""

.. autoclass:: prompt_toolkit.layout.CompletionsMenu
    :members:

.. autoclass:: prompt_toolkit.layout.MultiColumnCompletionsMenu
    :members:


Processors
""""""""""

.. automodule:: prompt_toolkit.layout.processors
    :members:


Utils
"""""

.. automodule:: prompt_toolkit.layout.utils
    :members:


Screen
""""""

.. automodule:: prompt_toolkit.layout.screen
    :members:


Widgets
-------

.. automodule:: prompt_toolkit.widgets
    :members: TextArea, Label, Button, Frame, Shadow, Box, VerticalLine,
        HorizontalLine, RadioList, Checkbox, ProgressBar, CompletionsToolbar,
        FormattedTextToolbar, SearchToolbar, SystemToolbar, ValidationToolbar,
        MenuContainer, MenuItem


Filters
-------

.. automodule:: prompt_toolkit.filters
    :members:

.. autoclass:: prompt_toolkit.filters.Filter
    :members:

.. autoclass:: prompt_toolkit.filters.Condition
    :members:

.. automodule:: prompt_toolkit.filters.utils
    :members:

.. automodule:: prompt_toolkit.filters.app
    :members:


Key binding
-----------

.. automodule:: prompt_toolkit.key_binding
    :members: KeyBindingsBase, KeyBindings, ConditionalKeyBindings,
        merge_key_bindings, DynamicKeyBindings

.. automodule:: prompt_toolkit.key_binding.defaults
    :members:

.. automodule:: prompt_toolkit.key_binding.vi_state
    :members:

.. automodule:: prompt_toolkit.key_binding.key_processor
    :members:


Eventloop
---------

.. automodule:: prompt_toolkit.eventloop
    :members: EventLoop, get_traceback_from_context, From, Return,
        ensure_future, create_event_loop, create_asyncio_event_loop,
        get_event_loop, set_event_loop, run_in_executor, call_from_executor,
        run_until_complete, Future, InvalidStateError

.. automodule:: prompt_toolkit.eventloop.posix
    :members:

.. automodule:: prompt_toolkit.eventloop.win32
    :members:

.. automodule:: prompt_toolkit.eventloop.asyncio_win32
    :members:

.. automodule:: prompt_toolkit.eventloop.asyncio_posix
    :members:


Input
-----

.. automodule:: prompt_toolkit.input
    :members: Input, DummyInput, create_input, create_pipe_input

.. automodule:: prompt_toolkit.input.vt100
    :members:

.. automodule:: prompt_toolkit.input.vt100_parser
    :members:

.. automodule:: prompt_toolkit.input.ansi_escape_sequences
    :members:

.. automodule:: prompt_toolkit.input.win32
    :members:

Output
------

.. automodule:: prompt_toolkit.output
    :members: Output, DummyOutput, ColorDepth, create_output,
        get_default_output, set_default_output

.. automodule:: prompt_toolkit.output.vt100
    :members:

.. automodule:: prompt_toolkit.output.win32
    :members:


Data structures
---------------

.. autoclass:: prompt_toolkit.layout.WindowRenderInfo
    :members:

.. autoclass:: prompt_toolkit.data_structures.Point
    :members:

.. autoclass:: prompt_toolkit.data_structures.Size
    :members:

Patch stdout
------------

.. automodule:: prompt_toolkit.patch_stdout
    :members: patch_stdout, StdoutProxy
