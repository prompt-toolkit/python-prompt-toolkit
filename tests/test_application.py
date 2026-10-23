from __future__ import annotations

import asyncio

import pytest

from prompt_toolkit.application import Application
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.renderer import Renderer


def test_renderer_is_not_reset_repeatedly_during_application_lifecycle(
    monkeypatch,
) -> None:
    reset_calls = 0
    reset_calls_before_render: list[int] = []
    original_reset = Renderer.reset

    def reset(self: Renderer, *args: object, **kwargs: object) -> None:
        nonlocal reset_calls
        reset_calls += 1
        original_reset(self, *args, **kwargs)

    monkeypatch.setattr(Renderer, "reset", reset)

    with create_pipe_input() as input:
        app: Application[None] = Application(
            input=input,
            output=DummyOutput(),
            before_render=lambda _: reset_calls_before_render.append(reset_calls),
        )
        app.run(pre_run=lambda: app.exit())

    assert reset_calls_before_render == [1, 1]
    assert reset_calls == 2


def test_resize_redraw_failure_quits_full_screen() -> None:
    class FullScreenOutput(DummyOutput):
        def __init__(self) -> None:
            self.alternate_screen_entered = 0
            self.alternate_screen_quit = 0

        def enter_alternate_screen(self) -> None:
            self.alternate_screen_entered += 1

        def quit_alternate_screen(self) -> None:
            self.alternate_screen_quit += 1

    output = FullScreenOutput()
    redraw_error = RuntimeError("redraw failed")
    render_count = 0

    def before_render(app: Application[None]) -> None:
        nonlocal render_count
        render_count += 1

        if render_count == 2:
            app.exit(exception=redraw_error)

        if render_count >= 2:
            raise redraw_error

    with create_pipe_input() as input:
        app: Application[None] = Application(
            full_screen=True,
            input=input,
            output=output,
            before_render=before_render,
        )

        def resize() -> None:
            with pytest.raises(RuntimeError, match="redraw failed"):
                app._on_resize()

        with pytest.raises(RuntimeError, match="redraw failed"):
            app.run(pre_run=lambda: asyncio.get_running_loop().call_soon(resize))

    assert output.alternate_screen_entered == 1
    assert output.alternate_screen_quit == 1
