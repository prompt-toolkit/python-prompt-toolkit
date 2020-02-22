#!/usr/bin/env python
"""
Read Windows input and print keys.
For testing terminal input.
"""
import asyncio

from prompt_toolkit.input.win32 import Win32Input
from prompt_toolkit.keys import Keys


async def main():
    input = Win32Input()
    done = asyncio.Event()

    def keys_ready():
        for key_press in input.read_keys():
            print(key_press)

            if key_press.key == Keys.ControlC:
                done.set()

    with input.raw_mode():
        with input.attach(keys_ready):
            await done.wait()


if __name__ == "__main__":
    asyncio.run(main())
