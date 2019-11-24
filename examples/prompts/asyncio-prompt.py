#!/usr/bin/env python
"""
(Python >= 3.5)
This is an example of how to prompt inside an application that uses the asyncio
eventloop. The ``prompt_toolkit`` library will make sure that when other
coroutines are writing to stdout, they write above the prompt, not destroying
the input line.
This example does several things:
    1. It starts a simple coroutine, printing a counter to stdout every second.
    2. It starts a simple input/echo app loop which reads from stdin.
Very important is the following patch. If you are passing stdin by reference to
other parts of the code, make sure that this patch is applied as early as
possible. ::
    sys.stdout = app.stdout_proxy()
"""

import asyncio

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession

loop = asyncio.get_event_loop()


async def print_counter():
    """
    Coroutine that prints counters.
    """
    i = 0
    while True:
        print('Counter: %i' % i)
        i += 1
        await asyncio.sleep(3)


async def interactive_shell():
    """
    Like `interactive_shell`, but doing things manual.
    """
    # Create Prompt.
    session = PromptSession('Say something: ')

    # Run echo loop. Read text from stdin, and reply it back.
    while True:
        try:
            result = await session.prompt_async()
            print('You said: "{0}"'.format(result))
        except (EOFError, KeyboardInterrupt):
            return


async def main():
    with patch_stdout():
        background_task = asyncio.ensure_future(print_counter())
        await interactive_shell()
        background_task.cancel()


if __name__ == '__main__':
    try:
        from asyncio import run
    except ImportError:
        asyncio.get_event_loop().run_until_complete(main())
    else:
        run(main())
