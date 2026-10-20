from __future__ import annotations

from asyncio import run, wait_for

import pytest

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.filters import Always, Condition, Never
from prompt_toolkit.formatted_text import fragment_list_to_text
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, UIContent, to_window
from prompt_toolkit.layout.dimension import to_dimension
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.widgets import Button, TextArea


def _to_text(button: Button) -> str:
    control = to_window(button).content
    return fragment_list_to_text(control.text())


def test_default_button():
    button = Button("Exit")
    assert _to_text(button) == "<   Exit   >"


def test_custom_button():
    button = Button("Exit", left_symbol="[", right_symbol="]")
    assert _to_text(button) == "[   Exit   ]"


@pytest.mark.parametrize(
    "multiline, enabled",
    [
        (True, True),
        (False, False),
        (Always(), True),
        (Never(), False),
        (Condition(lambda: True), True),
        (Condition(lambda: False), False),
    ],
)
def test_text_area_multiline_filter(multiline, enabled):
    area = TextArea(multiline=multiline, height=5, line_numbers=True, scrollbar=True)
    assert area.buffer.multiline() is enabled
    dimension = to_dimension(area.window.height)
    assert dimension.min == dimension.max == (5 if enabled else 1)
    get_content = lambda: UIContent(line_count=2)
    assert sum(m.get_width(get_content) for m in area.window.left_margins) == (
        3 if enabled else 0
    )
    assert sum(m.get_width(get_content) for m in area.window.right_margins) == (
        1 if enabled else 0
    )


def test_text_area_multiline_filter_updates_layout():
    enabled = False
    height = 5
    area = TextArea(
        multiline=Condition(lambda: enabled),
        height=lambda: height,
        line_numbers=True,
        scrollbar=True,
    )
    get_content = lambda: UIContent(line_count=2)

    for enabled, height in [(False, 5), (True, 5), (True, 7), (False, 7), (True, 7)]:
        assert area.buffer.multiline() is enabled
        dimension = to_dimension(area.window.height)
        assert dimension.min == dimension.max == (height if enabled else 1)
        assert sum(m.get_width(get_content) for m in area.window.left_margins) == (
            3 if enabled else 0
        )
        assert sum(m.get_width(get_content) for m in area.window.right_margins) == (
            1 if enabled else 0
        )


def test_text_area_multiline_filter_changes_enter_behavior():
    async def check():
        enabled = True
        bindings = KeyBindings()

        @bindings.add("c-t")
        def toggle(event):
            nonlocal enabled
            enabled = not enabled

        area = TextArea(
            multiline=Condition(lambda: enabled),
            accept_handler=lambda buffer: get_app().exit(result=buffer.text),
        )
        with create_pipe_input() as pipe_input:
            app = Application(
                layout=Layout(area),
                key_bindings=bindings,
                input=pipe_input,
                output=DummyOutput(),
            )
            pipe_input.send_text("first\r\x14second\r")
            assert await wait_for(app.run_async(), timeout=3) == "first\nsecond"

    run(check())
