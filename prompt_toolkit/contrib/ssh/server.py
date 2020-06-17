"""
Utility for running a prompt_toolkit application in an asyncssh server.
"""
import asyncio
import traceback
from typing import Awaitable, Callable, Optional, TextIO, cast

import asyncssh

from prompt_toolkit.application.current import AppSession, create_app_session
from prompt_toolkit.data_structures import Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output.vt100 import Vt100_Output

__all__ = ["PromptToolkitSSHSession", "PromptToolkitSSHServer"]


class PromptToolkitSSHSession(asyncssh.SSHServerSession):
    def __init__(
        self, interact: Callable[["PromptToolkitSSHSession"], Awaitable[None]]
    ) -> None:
        self.interact = interact
        self._chan = None
        self.app_session: Optional[AppSession] = None

        # PipInput object, for sending input in the CLI.
        # (This is something that we can use in the prompt_toolkit event loop,
        # but still write date in manually.)
        self._input = create_pipe_input()
        self._output = None

        # Output object. Don't render to the real stdout, but write everything
        # in the SSH channel.
        class Stdout:
            def write(s, data):
                if self._chan is not None:
                    self._chan.write(data.replace("\n", "\r\n"))

            def flush(s):
                pass

        self.stdout = cast(TextIO, Stdout())

    def _get_size(self) -> Size:
        """
        Callable that returns the current `Size`, required by Vt100_Output.
        """
        if self._chan is None:
            return Size(rows=20, columns=79)
        else:
            width, height, pixwidth, pixheight = self._chan.get_terminal_size()
            return Size(rows=height, columns=width)

    def connection_made(self, chan):
        self._chan = chan

    def shell_requested(self) -> bool:
        return True

    def session_started(self) -> None:
        asyncio.get_event_loop().create_task(self._interact())

    async def _interact(self) -> None:
        if self._chan is None:
            # Should not happen.
            raise Exception("`_interact` called before `connection_made`.")

        # Disable the line editing provided by asyncssh. Prompt_toolkit
        # provides the line editing.
        self._chan.set_line_mode(False)
        term = self._chan.get_terminal_type()

        self._output = Vt100_Output(
            self.stdout, self._get_size, term=term, write_binary=False
        )
        with create_app_session(input=self._input, output=self._output) as session:
            self.app_session = session
            try:
                await self.interact(self)
            except BaseException:
                traceback.print_exc()
            finally:
                # Close the connection.
                self._chan.close()

    def terminal_size_changed(self, width, height, pixwidth, pixheight):
        # Send resize event to the current application.
        if self.app_session and self.app_session.app:
            self.app_session.app._on_resize()

    def data_received(self, data, datatype):
        self._input.send_text(data)


class PromptToolkitSSHServer(asyncssh.SSHServer):
    """
    Run a prompt_toolkit application over an asyncssh server.

    This takes one argument, an `interact` function, which is called for each
    connection. This should be an asynchronous function that runs the
    prompt_toolkit applications. This function runs in an `AppSession`, which
    means that we can have multiple UI interactions concurrently.

    Example usage:

    .. code:: python

        async def interact(ssh_session: PromptToolkitSSHSession) -> None:
            await yes_no_dialog("my title", "my text").run_async()

            prompt_session = PromptSession()
            text = await prompt_session.prompt_async("Type something: ")
            print_formatted_text('You said: ', text)

        server = PromptToolkitSSHServer(interact=interact)
        loop = get_event_loop()
        loop.run_until_complete(
            asyncssh.create_server(
                lambda: MySSHServer(interact),
                "",
                port,
                server_host_keys=["/etc/ssh/..."],
            )
        )
        loop.run_forever()
    """

    def __init__(
        self, interact: Callable[[PromptToolkitSSHSession], Awaitable[None]]
    ) -> None:
        self.interact = interact

    def begin_auth(self, username):
        # No authentication.
        return False

    def session_requested(self) -> PromptToolkitSSHSession:
        return PromptToolkitSSHSession(self.interact)
