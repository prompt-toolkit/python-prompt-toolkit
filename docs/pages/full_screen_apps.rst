.. _full_screen_applications:

Building full screen applications
=================================

`prompt_toolkit` can be used to create complex full screen terminal
applications. Typically, an application consists of a layout (to describe the
graphical part) and a set of key bindings.

The sections below describe the components required for full screen
applications (or custom, non full screen applications), and how to assemble
them together.

.. warning:: This is going to change.

    The information below is still up to date, but we are planning to
    refactor some of the internal architecture of prompt_toolkit, to make it
    easier to build full screen applications. This will however be
    backwards-incompatible. The refactoring should probably be complete
    somewhere around half 2017.

Running the application
-----------------------

To run our final Full screen Application, we need three I/O objects, and
an :class:`~prompt_toolkit.application.Application` instance. These are passed
as arguments to :class:`~prompt_toolkit.interface.CommandLineInterface`.

The three I/O objects are:

    - An :class:`~prompt_toolkit.eventloop.base.EventLoop` instance. This is
      basically a while-true loop that waits for user input, and when it receives
      something (like a key press), it will send that to the application.
    - An :class:`~prompt_toolkit.input.Input` instance. This is an abstraction
      on the input stream (stdin).
    - An :class:`~prompt_toolkit.output.Output` instance. This is an
      abstraction on the output stream, and is called by the renderer.

The input and output objects are optional. However, the eventloop is always
required.

We'll come back to what the :class:`~prompt_toolkit.application.Application`
instance is later.

So, the only thing we actually need in order to run an application is the following:

.. code:: python

    from prompt_toolkit.interface import CommandLineInterface
    from prompt_toolkit.application import Application
    from prompt_toolkit.shortcuts import create_eventloop

    loop = create_eventloop()
    application = Application()
    cli = CommandLineInterface(application=application, eventloop=loop)
    # cli.run()
    print('Exiting')

.. note:: In the example above, we don't run the application yet, as otherwise
    it will hang indefinitely waiting for a signal to exit the event loop. This
    is why the `cli.run()` part is commented.

    (Actually, it would accept the `Enter` key by default. But that's only
    because by default, a buffer called `DEFAULT_BUFFER` has the focus; its
    :class:`~prompt_toolkit.buffer.AcceptAction` is configured to return the
    result when accepting, and there is a default `Enter` key binding that
    calls the :class:`~prompt_toolkit.buffer.AcceptAction` of the currently
    focussed buffer. However, the content of the `DEFAULT_BUFFER` buffer is not
    yet visible, so it's hard to see what's going on.)

Let's now bind a keyboard shortcut to exit:

Key bindings
------------

In order to react to user actions, we need to create a registry of keyboard
shortcuts to pass to our :class:`~prompt_toolkit.application.Application`.  The
easiest way to do so, is to use the
:class:`~prompt_toolkit.key_binding.manager.defaults.load_key_bindings`
function. This returns a `Registry` object that is already filled with the
default key bindings.

.. code:: python

    from prompt_toolkit.key_binding.defaults import load_key_bindings
    registry = load_key_bindings()

Update the `Application` constructor, and pass the registry as one of the
argument.

.. code:: python

    application = Application(key_bindings_registry=registry)

To register a new keyboard shortcut, we can use the
:meth:`~prompt_toolkit.key_binding.registry.Registry.add_binding` method as a
decorator of the key handler.

.. code:: python

    from prompt_toolkit.keys import Keys

    @registry.add_binding(Keys.ControlQ, eager=True)
    def exit_(event):
        """
        Pressing Ctrl-Q will exit the user interface.

        Setting a return value means: quit the event loop that drives the user
        interface and return this value from the `CommandLineInterface.run()` call.
        """
        event.cli.set_return_value(None)

In this particular example we use ``eager=True`` to trigger the callback as soon
as the shortcut `Ctrl-Q` is pressed. The callback is named ``exit_`` for clarity,
but it could have been named ``_`` (underscore) as well, because the we won't
refer to this name.


Creating a layout
-----------------

A `layout` is a composition of
:class:`~prompt_toolkit.layout.containers.Container` and
:class:`~prompt_toolkit.layout.controls.UIControl` that will describe the
disposition of various element on the user screen.

Various Layouts can refer to `Buffers` that have to be created and pass to the
application separately. This allow an application to have its layout changed,
without having to reconstruct buffers. You can imagine for example switching
from an horizontal to a vertical split panel layout and vice versa,

There are two types of classes that have to be combined to construct a layout:

- **containers** (:class:`~prompt_toolkit.layout.containers.Container`
  instances), which arrange the layout

- **user controls**
  (:class:`~prompt_toolkit.layout.controls.UIControl` instances), which
  generate the actual content


.. note::

   An important difference:

   - containers use *absolute coordinates*, and paint on a
     :class:`~prompt_toolkit.layout.screen.Screen` instance.
   - user controls create a :class:`~prompt_toolkit.layout.controls.UIContent`
     instance. This is a collection of lines that represent the actual
     content. A :class:`~prompt_toolkit.layout.controls.UIControl` is not aware
     of the screen.

+------------------------------------------------------+-----------------------------------------------------------+
| Abstract base class                                  | Examples                                                  |
+======================================================+===========================================================+
| :class:`~prompt_toolkit.layout.containers.Container` | :class:`~prompt_toolkit.layout.containers.HSplit`         |
|                                                      | :class:`~prompt_toolkit.layout.containers.VSplit`         |
|                                                      | :class:`~prompt_toolkit.layout.containers.FloatContainer` |
|                                                      | :class:`~prompt_toolkit.layout.containers.Window`         |
+------------------------------------------------------+-----------------------------------------------------------+
| :class:`~prompt_toolkit.layout.controls.UIControl`   | :class:`~prompt_toolkit.layout.controls.BufferControl`    |
|                                                      | :class:`~prompt_toolkit.layout.controls.TokenListControl` |
|                                                      | :class:`~prompt_toolkit.layout.controls.FillControl`      |
+------------------------------------------------------+-----------------------------------------------------------+


The :class:`~prompt_toolkit.layout.containers.Window` class itself is
particular: it is a :class:`~prompt_toolkit.layout.containers.Container` that
can contain a :class:`~prompt_toolkit.layout.controls.UIControl`. Thus, it's
the adaptor between the two.

The :class:`~prompt_toolkit.layout.containers.Window` class also takes care of
scrolling the content if the user control created a
:class:`~prompt_toolkit.layout.screen.Screen` that is larger than what was
available to the :class:`~prompt_toolkit.layout.containers.Window`.

Here is an example of a layout that displays the content of the default buffer
on the left, and displays ``"Hello world"`` on the right. In between it shows a
vertical line:

.. code:: python

    from prompt_toolkit.enums import DEFAULT_BUFFER
    from prompt_toolkit.layout.containers import VSplit, Window
    from prompt_toolkit.layout.controls import BufferControl, FillControl, TokenListControl
    from prompt_toolkit.layout.dimension import LayoutDimension as D

    from pygments.token import Token

    layout = VSplit([
        # One window that holds the BufferControl with the default buffer on the
        # left.
        Window(content=BufferControl(buffer_name=DEFAULT_BUFFER)),

        # A vertical line in the middle. We explicitely specify the width, to make
        # sure that the layout engine will not try to divide the whole width by
        # three for all these windows. The `FillControl` will simply fill the whole
        # window by repeating this character.
        Window(width=D.exact(1),
               content=FillControl('|', token=Token.Line)),

        # Display the text 'Hello world' on the right.
        Window(content=TokenListControl(
            get_tokens=lambda cli: [(Token, 'Hello world')])),
    ])

The previous section explains how to create an application, you can just pass
the currently created `layout` when you create the ``Application`` instance
using the ``layout=`` keyword argument.

.. code:: python

    app = Application(..., layout=layout, ...)


The rendering flow
^^^^^^^^^^^^^^^^^^

Understanding the rendering flow is important for understanding how
:class:`~prompt_toolkit.layout.containers.Container` and
:class:`~prompt_toolkit.layout.controls.UIControl` objects interact. We will
demonstrate it by explaining the flow around a
:class:`~prompt_toolkit.layout.controls.BufferControl`.

.. note::

    A :class:`~prompt_toolkit.layout.controls.BufferControl` is a
    :class:`~prompt_toolkit.layout.controls.UIControl` for displaying the
    content of a :class:`~prompt_toolkit.buffer.Buffer`. A buffer is the object
    that holds any editable region of text. Like all controls, it has to be
    wrapped into a :class:`~prompt_toolkit.layout.containers.Window`.

Let's take the following code:

.. code:: python

    from prompt_toolkit.enums import DEFAULT_BUFFER
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import BufferControl

    Window(content=BufferControl(buffer_name=DEFAULT_BUFFER))

What happens when a :class:`~prompt_toolkit.renderer.Renderer` objects wants a
:class:`~prompt_toolkit.layout.containers.Container` to be rendered on a
certain :class:`~prompt_toolkit.layout.screen.Screen`?

The visualisation happens in several steps:

1. The :class:`~prompt_toolkit.renderer.Renderer` calls the
   :meth:`~prompt_toolkit.layout.containers.Container.write_to_screen` method
   of a :class:`~prompt_toolkit.layout.containers.Container`.
   This is a request to paint the layout in a rectangle of a certain size.

   The :class:`~prompt_toolkit.layout.containers.Window` object then requests
   the :class:`~prompt_toolkit.layout.controls.UIControl` to create a
   :class:`~prompt_toolkit.layout.controls.UIContent` instance (by calling
   :meth:`~prompt_toolkit.layout.controls.UIControl.create_content`).
   The user control receives the dimensions of the window, but can still
   decide to create more or less content.

   Inside the :meth:`~prompt_toolkit.layout.controls.UIControl.create_content`
   method of :class:`~prompt_toolkit.layout.controls.UIControl`, there are
   several steps:

   2. First, the buffer's text is passed to the
      :meth:`~prompt_toolkit.layout.lexers.Lexer.lex_document` method of a
      :class:`~prompt_toolkit.layout.lexers.Lexer`. This returns a function which
      for a given line number, returns a token list for that line (that's a
      list of ``(Token, text)`` tuples).

   3. The token list is passed through a list of
      :class:`~prompt_toolkit.layout.processors.Processor` objects.
      Each processor can do a transformation for each line.
      (For instance, they can insert or replace some text.)

   4. The :class:`~prompt_toolkit.layout.controls.UIControl` returns a
      :class:`~prompt_toolkit.layout.controls.UIContent` instance which
      generates such a token lists for each lines.

The :class:`~prompt_toolkit.layout.containers.Window` receives the
:class:`~prompt_toolkit.layout.controls.UIContent` and then:

5. It calculates the horizontal and vertical scrolling, if applicable
   (if the content would take more space than what is available).

6. The content is copied to the correct absolute position
   :class:`~prompt_toolkit.layout.screen.Screen`, as requested by the
   :class:`~prompt_toolkit.renderer.Renderer`. While doing this, the
   :class:`~prompt_toolkit.layout.containers.Window` can possible wrap the
   lines, if line wrapping was configured.

Note that this process is lazy: if a certain line is not displayed in the
:class:`~prompt_toolkit.layout.containers.Window`, then it is not requested
from the :class:`~prompt_toolkit.layout.controls.UIContent`. And from there,
the line is not passed through the processors or even asked from the
:class:`~prompt_toolkit.layout.lexers.Lexer`.

Input processors
^^^^^^^^^^^^^^^^

An :class:`~prompt_toolkit.layout.processors.Processor` is an object that
processes the tokens of a line in a
:class:`~prompt_toolkit.layout.controls.BufferControl` before it's passed to a
:class:`~prompt_toolkit.layout.controls.UIContent` instance.

Some build-in processors:

+----------------------------------------------------------------------------+-----------------------------------------------------------+
| Processor                                                                  | Usage:                                                    |
+============================================================================+===========================================================+
| :class:`~prompt_toolkit.layout.processors.HighlightSearchProcessor`        | Highlight the current search results.                     |
+----------------------------------------------------------------------------+-----------------------------------------------------------+
| :class:`~prompt_toolkit.layout.processors.HighlightSelectionProcessor`     | Highlight the selection.                                  |
+----------------------------------------------------------------------------+-----------------------------------------------------------+
| :class:`~prompt_toolkit.layout.processors.PasswordProcessor`               | Display input as asterisks. (``*`` characters).           |
+----------------------------------------------------------------------------+-----------------------------------------------------------+
| :class:`~prompt_toolkit.layout.processors.BracketsMismatchProcessor`       | Highlight open/close mismatches for brackets.             |
+----------------------------------------------------------------------------+-----------------------------------------------------------+
| :class:`~prompt_toolkit.layout.processors.BeforeInput`                     | Insert some text before.                                  |
+----------------------------------------------------------------------------+-----------------------------------------------------------+
| :class:`~prompt_toolkit.layout.processors.AfterInput`                      | Insert some text after.                                   |
+----------------------------------------------------------------------------+-----------------------------------------------------------+
| :class:`~prompt_toolkit.layout.processors.AppendAutoSuggestion`            | Append auto suggestion text.                              |
+----------------------------------------------------------------------------+-----------------------------------------------------------+
| :class:`~prompt_toolkit.layout.processors.ShowLeadingWhiteSpaceProcessor`  | Visualise leading whitespace.                             |
+----------------------------------------------------------------------------+-----------------------------------------------------------+
| :class:`~prompt_toolkit.layout.processors.ShowTrailingWhiteSpaceProcessor` | Visualise trailing whitespace.                            |
+----------------------------------------------------------------------------+-----------------------------------------------------------+
| :class:`~prompt_toolkit.layout.processors.TabsProcessor`                   | Visualise tabs as `n` spaces, or some symbols.            |
+----------------------------------------------------------------------------+-----------------------------------------------------------+



The ``TokenListControl``
^^^^^^^^^^^^^^^^^^^^^

Custom user controls
^^^^^^^^^^^^^^^^^^^^

The Window class
^^^^^^^^^^^^^^^^

The :class:`~prompt_toolkit.layout.containers.Window` class exposes many
interesting functionality that influences the behaviour of user controls.




Buffers
-------


The focus stack
---------------


The ``Application`` instance
----------------------------

The :class:`~prompt_toolkit.application.Application` instance is where all the
components for a prompt_toolkit application come together.

.. note:: Actually, not *all* the components; just everything that is not
    dependent on I/O (i.e. all components except for the eventloop and the
    input/output objects).

    This way, it's possible to create an
    :class:`~prompt_toolkit.application.Application` instance and later decide
    to run it on an asyncio eventloop or in a telnet server.

.. code:: python

    from prompt_toolkit.application import Application

    application = Application(
        layout=layout,
        key_bindings_registry=registry,

        # Let's add mouse support as well.
        mouse_support=True,

        # For fullscreen:
        use_alternate_screen=True)

We are talking about full screen applications, so it's important to pass
``use_alternate_screen=True``. This switches to the alternate terminal buffer.


.. _filters:

Filters (reactivity)
--------------------

Many places in `prompt_toolkit` expect a boolean. For instance, for determining
the visibility of some part of the layout (it can be either hidden or visible),
or a key binding filter (the binding can be active on not) or the
``wrap_lines`` option of
:class:`~prompt_toolkit.layout.controls.BufferControl`, etc.

These booleans however are often dynamic and can change at runtime. For
instance, the search toolbar should only be visible when the user is actually
searching (when the search buffer has the focus). The ``wrap_lines`` option
could be changed with a certain key binding. And that key binding could only
work when the default buffer got the focus.

In `prompt_toolkit`, we decided to reduce the amount of state in the whole
framework, and apply a simple kind of reactive programming to describe the flow
of these booleans as expressions. (It's one-way only: if a key binding needs to
know whether it's active or not, it can follow this flow by evaluating an
expression.)

There are two kind of expressions:

- :class:`~prompt_toolkit.filters.SimpleFilter`,
  which wraps an expression that takes no input, and evaluates to a boolean.

- :class:`~prompt_toolkit.filters.CLIFilter`, which takes a
  :class:`~prompt_toolkit.interface.CommandLineInterface` as input.


Most code in prompt_toolkit that expects a boolean will also accept a
:class:`~prompt_toolkit.filters.CLIFilter`.

One way to create a :class:`~prompt_toolkit.filters.CLIFilter` instance is by
creating a :class:`~prompt_toolkit.filters.Condition`. For instance, the
following condition will evaluate to ``True`` when the user is searching:

.. code:: python

    from prompt_toolkit.filters import Condition
    from prompt_toolkit.enums import DEFAULT_BUFFER

    is_searching = Condition(lambda cli: cli.is_searching)

This filter can then be used in a key binding, like in the following snippet:

.. code:: python

    from prompt_toolkit.key_binding.defaults import load_key_bindings

    registry = load_key_bindings()

    @registry.add_binding(Keys.ControlT, filter=is_searching)
    def _(event):
        # Do, something, but only when searching.
        pass

There are many built-in filters, ready to use:

- :class:`~prompt_toolkit.filters.HasArg`
- :class:`~prompt_toolkit.filters.HasCompletions`
- :class:`~prompt_toolkit.filters.HasFocus`
- :class:`~prompt_toolkit.filters.InFocusStack`
- :class:`~prompt_toolkit.filters.HasSearch`
- :class:`~prompt_toolkit.filters.HasSelection`
- :class:`~prompt_toolkit.filters.HasValidationError`
- :class:`~prompt_toolkit.filters.IsAborting`
- :class:`~prompt_toolkit.filters.IsDone`
- :class:`~prompt_toolkit.filters.IsMultiline`
- :class:`~prompt_toolkit.filters.IsReadOnly`
- :class:`~prompt_toolkit.filters.IsReturning`
- :class:`~prompt_toolkit.filters.RendererHeightIsKnown`

Further, these filters can be chained by the ``&`` and ``|`` operators or
negated by the ``~`` operator.

Some examples:

.. code:: python

    from prompt_toolkit.key_binding.defaults import load_key_bindings
    from prompt_toolkit.filters import HasSearch, HasSelection

    registry = load_key_bindings()

    @registry.add_binding(Keys.ControlT, filter=~is_searching)
    def _(event):
        # Do, something, but not when when searching.
        pass

    @registry.add_binding(Keys.ControlT, filter=HasSearch() | HasSelection())
    def _(event):
        # Do, something, but not when when searching.
        pass


Input hooks
-----------


Running on the ``asyncio`` event loop
-------------------------------------
