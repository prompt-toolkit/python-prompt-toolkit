"""
PromptToolkitReader: helper to provide streamreader-like functionality in a
prompt_toolkit application.
"""
import asyncio
from asyncio import StreamReader
from typing import Optional

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.output import DummyOutput


class PromptToolkitReader:
    """
    Tool to provide StreamReader-like functionality in a prompt_toolkit
    Application session. This is useful when we have a prompt_toolkit
    SSH/telnet session, and sometimes we want to use a PromptSession to ask the
    user for input (with line editing functionality), but later we want to have
    a raw streamreader to read from stdin.

    This is a workaround because prompt_toolkit does not have a StreamReader
    available at any abstraction layer for this. So what we do is create a
    dummy application that intercepts every key stroke and feeds it back into a
    streamreader.

    It's likely that this implementation performs badly or contains bugs.
    """

    def __init__(self) -> None:
        self.reader = StreamReader()
        self._app: Optional[Application] = None
        self._f: Optional[asyncio.Future] = None

    async def __aenter__(self) -> "PromptToolkitReader":
        self._app = self._create_app()
        self._f = asyncio.create_task(self._app.run_async())
        return self

    async def __aexit__(self, *a) -> None:
        if self._app is not None:
            self._app.exit()

        if self._f is not None:
            await self._f

    def _create_app(self) -> Application:
        kb = KeyBindings()

        @kb.add("<any>", eager=True)
        def _(event):
            data = event.data.replace("\r", "\n")
            self.reader._buffer.extend(data.encode("utf-8"))
            self.reader._wakeup_waiter()

        return Application(key_bindings=kb, output=DummyOutput())


async def main() -> None:
    """
    Example usage.
    """
    async with PromptToolkitReader() as pt_reader:
        print("Calling streamreader.readline(). Type something and press ENTER.")
        line = await pt_reader.reader.readline()
        print(line)


if __name__ == "__main__":
    asyncio.run(main())
