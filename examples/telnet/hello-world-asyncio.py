#!/usr/bin/env python
"""
A simple Telnet application that asks for input and responds.

The interaction function is an asyncio coroutine.

WARNING: This is experimental! Prompt_toolkit TaskLocals don't work together
         with asyncio coroutines. This is also why we have to specify the
         output and input manually.
"""
import asyncio
import logging

from prompt_toolkit.contrib.telnet.server import TelnetServer
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop
from prompt_toolkit.shortcuts import PromptSession

# Set up logging
logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

# Tell prompt_toolkit to use the asyncio event loop.
use_asyncio_event_loop()


async def interact(connection):
    session = PromptSession(output=connection.vt100_output, input=connection.vt100_input)

    connection.erase_screen()
    connection.send('Welcome!\n')

    # Ask for input.
    result = await session.prompt(message='Say something: ', async_=True)

    # Send output.
    connection.send('You said: {}\n'.format(result))
    connection.send('Bye.\n')


def main():
    server = TelnetServer(interact=interact, port=2323)
    server.start()
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    main()
