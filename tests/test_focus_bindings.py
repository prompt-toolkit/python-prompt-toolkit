from __future__ import annotations

from contextlib import contextmanager

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import set_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.screen import Screen
from prompt_toolkit.output import DummyOutput


class _RecordingOutput(DummyOutput):
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[int, ...]]] = []

    @property
    def supports_focus_reporting(self) -> bool:
        return True

    def enable_focus_reporting(self) -> None:
        self.calls.append(("enable_focus_reporting", ()))

    def disable_focus_reporting(self) -> None:
        self.calls.append(("disable_focus_reporting", ()))

    def cursor_backward(self, amount: int) -> None:
        self.calls.append(("cursor_backward", (amount,)))

    def cursor_up(self, amount: int) -> None:
        self.calls.append(("cursor_up", (amount,)))

    def erase_down(self) -> None:
        self.calls.append(("erase_down", ()))


@contextmanager
def _create_app(output: DummyOutput):
    with create_pipe_input() as pipe_input:
        app = Application(
            layout=Layout(Window()),
            input=pipe_input,
            output=output,
        )

        def create_background_task(coroutine, **kwargs):
            coroutine.close()
            return None

        app.create_background_task = create_background_task

        with set_app(app):
            yield app


def test_focus_in_erases_and_invalidates_screen():
    output = _RecordingOutput()

    with _create_app(output) as app:
        invalidated = False

        def invalidate() -> None:
            nonlocal invalidated
            invalidated = True

        app.invalidate = invalidate
        app.renderer._last_screen = Screen()
        app.renderer._in_alternate_screen = True
        app.renderer._cursor_pos = Point(x=7, y=2)
        output.calls.clear()

        app.key_processor.feed(KeyPress(Keys.FocusIn, "\x1b[I"))
        app.key_processor.process_keys()

        assert app.renderer._last_screen is None
        assert app.renderer._in_alternate_screen
        assert invalidated
        assert output.calls == [
            ("cursor_backward", (7,)),
            ("cursor_up", (2,)),
            ("erase_down", ()),
        ]


def test_renderer_enables_and_disables_focus_reporting():
    output = _RecordingOutput()

    with _create_app(output) as app:
        app.renderer.render(app, app.layout)
        app.renderer.render(app, app.layout)

        focus_calls = [name for name, _ in output.calls if "focus_reporting" in name]
        assert focus_calls == ["enable_focus_reporting"]

        app.renderer.reset()

        focus_calls = [name for name, _ in output.calls if "focus_reporting" in name]
        assert focus_calls == ["enable_focus_reporting", "disable_focus_reporting"]
