from __future__ import annotations

import pytest

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import set_app
from prompt_toolkit.formatted_text import fragment_list_to_text
from prompt_toolkit.input import DummyInput
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout, to_window
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.widgets import Button, MenuContainer, MenuItem, TextArea


def _to_text(button: Button) -> str:
    control = to_window(button).content
    return fragment_list_to_text(control.text())


def test_default_button():
    button = Button("Exit")
    assert _to_text(button) == "<   Exit   >"


def test_custom_button():
    button = Button("Exit", left_symbol="[", right_symbol="]")
    assert _to_text(button) == "[   Exit   ]"


@pytest.mark.parametrize("disabled", [False, True])
@pytest.mark.parametrize("depth", [0, 1, 2])
def test_menu_keyboard_activation_respects_disabled(disabled, depth):
    calls = []
    item = MenuItem("Action", handler=lambda: calls.append(True), disabled=disabled)
    menu_items = [item]
    for _ in range(depth):
        menu_items = [MenuItem("Submenu", children=menu_items)]

    body = TextArea()
    menu = MenuContainer(body=body, menu_items=menu_items)
    app = Application(
        layout=Layout(menu, focused_element=body),
        input=DummyInput(),
        output=DummyOutput(),
    )
    # These complete key sequences do not need an asynchronous timeout.
    app.timeoutlen = None
    app.layout.focus(menu.window)

    navigation = [] if depth == 0 else [Keys.Down] + [Keys.Right] * (depth - 1)
    with set_app(app):
        for key in [*navigation, Keys.ControlM]:
            app.key_processor.feed(KeyPress(key))
            app.key_processor.process_keys()

    assert calls == ([] if disabled else [True])
    assert app.layout.has_focus(menu.window if disabled else body)


def test_menu_keyboard_activation_checks_current_disabled_state():
    calls = []
    item = MenuItem("Action", handler=lambda: calls.append(True))
    body = TextArea()
    menu = MenuContainer(body=body, menu_items=[MenuItem("File", children=[item])])
    app = Application(
        layout=Layout(menu, focused_element=body),
        input=DummyInput(),
        output=DummyOutput(),
    )
    app.timeoutlen = None
    app.layout.focus(menu.window)

    with set_app(app):
        app.key_processor.feed(KeyPress(Keys.Down))
        app.key_processor.process_keys()

        item.disabled = True
        app.key_processor.feed(KeyPress(Keys.ControlM))
        app.key_processor.process_keys()
        assert calls == []
        assert app.layout.has_focus(menu.window)

        item.disabled = False
        app.key_processor.feed(KeyPress(Keys.ControlM))
        app.key_processor.process_keys()
        assert calls == [True]
        assert app.layout.has_focus(body)
