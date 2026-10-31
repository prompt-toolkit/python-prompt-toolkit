from __future__ import annotations

import pytest

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import set_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import fragment_list_to_text
from prompt_toolkit.input import DummyInput
from prompt_toolkit.layout import Layout, to_window
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Screen, WritePosition
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.widgets import Button, CheckboxList, RadioList


def _to_text(button: Button) -> str:
    control = to_window(button).content
    return fragment_list_to_text(control.text())


def test_default_button():
    button = Button("Exit")
    assert _to_text(button) == "<   Exit   >"


def test_custom_button():
    button = Button("Exit", left_symbol="[", right_symbol="]")
    assert _to_text(button) == "[   Exit   ]"


def _render_list(app, widget):
    """Render a short viewport, including the real screen-coordinate handlers."""
    app.layout.update_parents_relations()
    app.render_counter += 1
    handlers = MouseHandlers()
    widget.window.write_to_screen(
        Screen(), handlers, WritePosition(0, 0, 20, 3), "", True, None
    )
    return handlers


def _mouse_event(handlers, event_type):
    return handlers.mouse_handlers[1][1](
        MouseEvent(
            Point(x=1, y=1),
            event_type,
            MouseButton.LEFT
            if event_type == MouseEventType.MOUSE_UP
            else MouseButton.NONE,
            frozenset(),
        )
    )


@pytest.mark.parametrize("widget_class", [RadioList, CheckboxList])
@pytest.mark.parametrize("focused", [True, False])
def test_dialog_list_mouse_wheel_scrolls(widget_class, focused):
    widget = widget_class([(i, str(i)) for i in range(10)])
    app = Application(layout=Layout(widget), input=DummyInput(), output=DummyOutput())
    if not focused:
        button = Button("Other")
        app.layout = Layout(HSplit([widget, button]), focused_element=button)
    current_value = widget.current_value
    current_values = widget.current_values[:]

    with set_app(app):
        handlers = _render_list(app, widget)
        for expected_scroll in [1, 2, 3, 4, 5, 6, 7, 7, 7]:
            _mouse_event(handlers, MouseEventType.SCROLL_DOWN)
            handlers = _render_list(app, widget)
            assert widget.window.vertical_scroll == expected_scroll
            assert 0 <= widget._selected_index < 10
            assert widget.current_value == current_value
            assert widget.current_values == current_values

        for expected_scroll in [6, 5, 4, 3, 2, 1, 0, 0, 0]:
            _mouse_event(handlers, MouseEventType.SCROLL_UP)
            handlers = _render_list(app, widget)
            assert widget.window.vertical_scroll == expected_scroll
            assert 0 <= widget._selected_index < 10
            assert widget.current_value == current_value
            assert widget.current_values == current_values

        # Screen coordinates must still select the correct item after scrolling.
        for _ in range(2):
            _mouse_event(handlers, MouseEventType.SCROLL_DOWN)
            handlers = _render_list(app, widget)
        _mouse_event(handlers, MouseEventType.MOUSE_UP)
        assert widget._selected_index == 3
        if isinstance(widget, CheckboxList):
            assert widget.current_values == [3]
            handlers = _render_list(app, widget)
            _mouse_event(handlers, MouseEventType.MOUSE_UP)
            assert widget.current_values == []
        else:
            assert widget.current_value == 3


def test_radio_list_mouse_wheel_select_on_focus():
    widget = RadioList(
        [(i, str(i)) for i in range(10)], default=2, select_on_focus=True
    )
    app = Application(layout=Layout(widget), input=DummyInput(), output=DummyOutput())

    with set_app(app):
        handlers = _render_list(app, widget)
        assert widget.window.vertical_scroll == 0
        # Scrolling does not change selection while the cursor remains visible.
        for expected_scroll in [1, 2]:
            _mouse_event(handlers, MouseEventType.SCROLL_DOWN)
            handlers = _render_list(app, widget)
            assert widget.window.vertical_scroll == expected_scroll
            assert widget.current_value == 2
        # Once needed, move the cursor and honor select_on_focus.
        _mouse_event(handlers, MouseEventType.SCROLL_DOWN)
        handlers = _render_list(app, widget)
        assert widget.window.vertical_scroll == 3
        assert widget._selected_index == widget.current_value == 3
        for expected_scroll in [2, 1]:
            _mouse_event(handlers, MouseEventType.SCROLL_UP)
            handlers = _render_list(app, widget)
            assert widget.window.vertical_scroll == expected_scroll
            assert widget.current_value == 3
        _mouse_event(handlers, MouseEventType.SCROLL_UP)
        _render_list(app, widget)
        assert widget.window.vertical_scroll == 0
        assert widget._selected_index == widget.current_value == 2
