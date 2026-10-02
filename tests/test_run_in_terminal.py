"""
Test how `in_terminal` repaints the application afterwards.
"""

from __future__ import annotations

import asyncio
import io

from prompt_toolkit.application import Application, in_terminal
from prompt_toolkit.data_structures import Size
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.layout import FormattedTextControl, HSplit, Layout, Window
from prompt_toolkit.output.vt100 import Vt100_Output


class _TTY(io.StringIO):
    "Emulate a terminal stdout, so that the output responds to CPR."

    def isatty(self) -> bool:
        return True


def _run(send_cpr_response: bool) -> list[bool]:
    """
    Run an inline application, run `in_terminal` once it got its first CPR
    response, and return for each paint after that (until exiting) whether
    the renderer knew the space below the cursor.
    """
    heights_known: list[bool] = []

    async def main() -> None:
        with create_pipe_input() as inp:
            app: Application[None] = Application(
                layout=Layout(
                    HSplit(
                        [
                            Window(FormattedTextControl("input"), height=1),
                            Window(),
                            Window(FormattedTextControl("toolbar"), height=1),
                        ]
                    )
                ),
                input=inp,
                output=Vt100_Output(_TTY(), lambda: Size(rows=24, columns=80)),
            )

            async def suspend() -> None:
                # Answer the CPR request done when the application started.
                inp.send_text("\x1b[1;1R")
                await app.renderer.wait_for_cpr_responses()

                def after_render(_: object) -> None:
                    if not app.is_done:
                        heights_known.append(app.renderer.height_is_known)

                async with in_terminal():
                    app.after_render += after_render
                    if send_cpr_response:
                        # Input is detached here. This is read once it gets
                        # attached again, after `in_terminal` requests the
                        # cursor position.
                        inp.send_text("\x1b[5;1R")

                app.exit()

            app.pre_run_callables.append(lambda: app.create_background_task(suspend()))
            await app.run_async()

    asyncio.run(main())
    return heights_known


def test_in_terminal_repaints_after_cpr_response():
    # Paint once, knowing the available height, so that the layout doesn't
    # jump.
    assert _run(send_cpr_response=True) == [True]


def test_in_terminal_repaints_without_cpr_response():
    # When the response doesn't arrive, still repaint after the timeout.
    assert _run(send_cpr_response=False) == [False]
