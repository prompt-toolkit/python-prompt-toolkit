from __future__ import annotations

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
