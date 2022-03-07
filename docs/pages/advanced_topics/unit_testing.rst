.. _unit_testing:

Unit testing
============

Testing user interfaces is not always obvious. Here are a few tricks for
testing prompt_toolkit applications.


`PosixPipeInput` and `DummyOutput`
----------------------------------

During the creation of a prompt_toolkit
:class:`~prompt_toolkit.application.Application`, we can specify what input and
output device to be used. By default, these are output objects that correspond
with `sys.stdin` and `sys.stdout`. In unit tests however, we want to replace
these.

- For the input, we want a "pipe input". This is an input device, in which we
  can programatically send some input. It can be created with
  :func:`~prompt_toolkit.input.create_pipe_input`, and that return either a
  :class:`~prompt_toolkit.input.posix_pipe.PosixPipeInput` or a
  :class:`~prompt_toolkit.input.win32_pipe.Win32PipeInput` depending on the
  platform.
- For the output, we want a :class:`~prompt_toolkit.output.DummyOutput`. This is
  an output device that doesn't render anything. We don't want to render
  anything to `sys.stdout` in the unit tests.

.. note::

    Typically, we don't want to test the bytes that are written to
    `sys.stdout`, because these can change any time when the rendering
    algorithm changes, and are not so meaningful anyway. Instead, we want to
    test the return value from the
    :class:`~prompt_toolkit.application.Application` or test how data
    structures (like text buffers) change over time.

So we programmatically feed some input to the input pipe, have the key
bindings process the input and then test what comes out of it. 

In the following example we use a
:class:`~prompt_toolkit.shortcuts.PromptSession`, but the same works for any
:class:`~prompt_toolkit.application.Application`.

.. code:: python

    from prompt_toolkit.shortcuts import PromptSession
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    def test_prompt_session():
        with create_pipe_input() as inp:
            inp.send_text("hello\n")
            session = PromptSession(
                input=inp,
                output=DummyOutput(),
            )

            result = session.prompt()

        assert result == "hello"

In the above example, don't forget to send the `\\n` character to accept the
prompt, otherwise the :class:`~prompt_toolkit.application.Application` will
wait forever for some more input to receive.

Using an :class:`~prompt_toolkit.application.current.AppSession`
----------------------------------------------------------------

Sometimes it's not convenient to pass input or output objects to the
:class:`~prompt_toolkit.application.Application`, and in some situations it's
not even possible at all.
This happens when these parameters are not passed down the call stack, through
all function calls.

An easy way to specify which input/output to use for all applications, is by
creating an :class:`~prompt_toolkit.application.current.AppSession` with this
input/output and running all code in that
:class:`~prompt_toolkit.application.current.AppSession`. This way, we don't
need to inject it into every :class:`~prompt_toolkit.application.Application`
or :func:`~prompt_toolkit.shortcuts.print_formatted_text` call.

Here is an example where we use
:func:`~prompt_toolkit.application.create_app_session`:

.. code:: python

    from prompt_toolkit.application import create_app_session
    from prompt_toolkit.shortcuts import print_formatted_text
    from prompt_toolkit.output import DummyOutput

    def test_something():
        with create_app_session(output=DummyOutput()):
            ...
            print_formatted_text('Hello world')
            ...

Pytest fixtures
---------------

In order to get rid of the boilerplate of creating the input, the
:class:`~prompt_toolkit.output.DummyOutput`, and the
:class:`~prompt_toolkit.application.current.AppSession`, we create a
single fixture that does it for every test. Something like this:

.. code:: python

    import pytest
    from prompt_toolkit.application import create_app_session
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    @pytest.fixture(autouse=True, scope="function")
    def mock_input():
        with create_pipe_input() as pipe_input:
            with create_app_session(input=pipe_input, output=DummyOutput()):
                yield pipe_input


Type checking
-------------

Prompt_toolkit 3.0 is fully type annotated. This means that if a
prompt_toolkit application is typed too, it can be verified with mypy. This is
complementary to unit tests, but also great for testing for correctness.
