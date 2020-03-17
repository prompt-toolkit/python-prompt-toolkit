.. _input_hooks:


Input hooks
===========

Input hooks are a tool for inserting an external event loop into the
prompt_toolkit event loop, so that the other loop can run as long as
prompt_toolkit (actually asyncio) is idle. This is used in applications like
`IPython <https://ipython.org/>`_, so that GUI toolkits can display their
windows while we wait at the prompt for user input.

As a consequence, we will "trampoline" back and forth between two event loops.

.. note::

    This will use a :class:`~asyncio.SelectorEventLoop`, not the :class:
    :class:`~asyncio.ProactorEventLoop` (on Windows) due to the way the
    implementation works (contributions are welcome to make that work).


.. code:: python

    from prompt_toolkit.eventloop.inputhook import set_eventloop_with_inputhook

    def inputhook(inputhook_context):
        # At this point, we run the other loop. This loop is supposed to run
        # until either `inputhook_context.fileno` becomes ready for reading or
        # `inputhook_context.input_is_ready()` returns True.

        # A good way is to register this file descriptor in this other event
        # loop with a callback that stops this loop when this FD becomes ready.
        # There is no need to actually read anything from the FD.

        while True:
            ...

    set_eventloop_with_inputhook(inputhook)

    # Any asyncio code at this point will now use this new loop, with input
    # hook installed.
