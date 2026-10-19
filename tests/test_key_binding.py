from __future__ import annotations

from contextlib import contextmanager

import pytest

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import set_app
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPress, KeyProcessor
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.output import DummyOutput


class Handlers:
    def __init__(self):
        self.called = []

    def __getattr__(self, name):
        def func(event):
            self.called.append(name)

        return func


@contextmanager
def set_dummy_app():
    """
    Return a context manager that makes sure that this dummy application is
    active. This is important, because we need an `Application` with
    `is_done=False` flag, otherwise no keys will be processed.
    """
    with create_pipe_input() as pipe_input:
        app = Application(
            layout=Layout(Window()),
            output=DummyOutput(),
            input=pipe_input,
        )

        def create_background_task(coroutine, **kw):
            coroutine.close()
            return None

        # Don't start background tasks for these tests. The `KeyProcessor`
        # wants to create a background task for flushing keys. We can ignore it
        # here for these tests.
        # This patch is not clean. In the future, when we can use Taskgroups,
        # the `Application` should pass its task group to the constructor of
        # `KeyProcessor`. That way, it doesn't have to do a lookup using
        # `get_app()`.
        app.create_background_task = create_background_task

        with set_app(app):
            yield


@pytest.fixture
def handlers():
    return Handlers()


@pytest.fixture
def bindings(handlers):
    bindings = KeyBindings()
    bindings.add(Keys.ControlX, Keys.ControlC)(handlers.controlx_controlc)
    bindings.add(Keys.ControlX)(handlers.control_x)
    bindings.add(Keys.ControlD)(handlers.control_d)
    bindings.add(Keys.ControlSquareClose, Keys.Any)(handlers.control_square_close_any)

    return bindings


@pytest.fixture
def processor(bindings):
    return KeyProcessor(bindings)


def test_remove_bindings(handlers):
    with set_dummy_app():
        h = handlers.controlx_controlc
        h2 = handlers.controld

        # Test passing a handler to the remove() function.
        bindings = KeyBindings()
        bindings.add(Keys.ControlX, Keys.ControlC)(h)
        bindings.add(Keys.ControlD)(h2)
        assert len(bindings.bindings) == 2
        bindings.remove(h)
        assert len(bindings.bindings) == 1

        # Test passing a key sequence to the remove() function.
        bindings = KeyBindings()
        bindings.add(Keys.ControlX, Keys.ControlC)(h)
        bindings.add(Keys.ControlD)(h2)
        assert len(bindings.bindings) == 2
        bindings.remove(Keys.ControlX, Keys.ControlC)
        assert len(bindings.bindings) == 1


def test_feed_simple(processor, handlers):
    with set_dummy_app():
        processor.feed(KeyPress(Keys.ControlX, "\x18"))
        processor.feed(KeyPress(Keys.ControlC, "\x03"))
        processor.process_keys()

        assert handlers.called == ["controlx_controlc"]


def test_feed_several(processor, handlers):
    with set_dummy_app():
        # First an unknown key first.
        processor.feed(KeyPress(Keys.ControlQ, ""))
        processor.process_keys()

        assert handlers.called == []

        # Followed by a know key sequence.
        processor.feed(KeyPress(Keys.ControlX, ""))
        processor.feed(KeyPress(Keys.ControlC, ""))
        processor.process_keys()

        assert handlers.called == ["controlx_controlc"]

        # Followed by another unknown sequence.
        processor.feed(KeyPress(Keys.ControlR, ""))
        processor.feed(KeyPress(Keys.ControlS, ""))

        # Followed again by a know key sequence.
        processor.feed(KeyPress(Keys.ControlD, ""))
        processor.process_keys()

        assert handlers.called == ["controlx_controlc", "control_d"]


def test_control_square_closed_any(processor, handlers):
    with set_dummy_app():
        processor.feed(KeyPress(Keys.ControlSquareClose, ""))
        processor.feed(KeyPress("C", "C"))
        processor.process_keys()

        assert handlers.called == ["control_square_close_any"]


def test_common_prefix(processor, handlers):
    with set_dummy_app():
        # Sending Control_X should not yet do anything, because there is
        # another sequence starting with that as well.
        processor.feed(KeyPress(Keys.ControlX, ""))
        processor.process_keys()

        assert handlers.called == []

        # When another key is pressed, we know that we did not meant the longer
        # "ControlX ControlC" sequence and the callbacks are called.
        processor.feed(KeyPress(Keys.ControlD, ""))
        processor.process_keys()

        assert handlers.called == ["control_x", "control_d"]


def test_previous_key_sequence(processor):
    """
    test whether we receive the correct previous_key_sequence.
    """
    with set_dummy_app():
        events = []

        def handler(event):
            events.append(event)

        # Build registry.
        registry = KeyBindings()
        registry.add("a", "a")(handler)
        registry.add("b", "b")(handler)
        processor = KeyProcessor(registry)

        # Create processor and feed keys.
        processor.feed(KeyPress("a", "a"))
        processor.feed(KeyPress("a", "a"))
        processor.feed(KeyPress("b", "b"))
        processor.feed(KeyPress("b", "b"))
        processor.process_keys()

        # Test.
        assert len(events) == 2
        assert len(events[0].key_sequence) == 2
        assert events[0].key_sequence[0].key == "a"
        assert events[0].key_sequence[0].data == "a"
        assert events[0].key_sequence[1].key == "a"
        assert events[0].key_sequence[1].data == "a"
        assert events[0].previous_key_sequence == []

        assert len(events[1].key_sequence) == 2
        assert events[1].key_sequence[0].key == "b"
        assert events[1].key_sequence[0].data == "b"
        assert events[1].key_sequence[1].key == "b"
        assert events[1].key_sequence[1].data == "b"
        assert len(events[1].previous_key_sequence) == 2
        assert events[1].previous_key_sequence[0].key == "a"
        assert events[1].previous_key_sequence[0].data == "a"
        assert events[1].previous_key_sequence[1].key == "a"
        assert events[1].previous_key_sequence[1].data == "a"


@pytest.mark.parametrize("initial_global", [False, True])
@pytest.mark.parametrize("wrap_merged", [False, True])
def test_global_bindings_evaluate_filters_dynamically(
    handlers, initial_global, wrap_merged
):
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.key_binding.key_bindings import (
        GlobalOnlyKeyBindings,
        merge_key_bindings,
    )

    global_enabled = initial_global
    binding_enabled = True
    bindings = KeyBindings()
    handler = handlers.dynamic
    bindings.add(
        "a",
        "b",
        filter=Condition(lambda: binding_enabled),
        is_global=Condition(lambda: global_enabled),
    )(handler)
    global_bindings = GlobalOnlyKeyBindings(bindings)
    registry = merge_key_bindings([global_bindings]) if wrap_merged else global_bindings

    def active_handlers(prefix=False):
        if prefix:
            matches = registry.get_bindings_starting_with_keys(("a",))
        else:
            matches = registry.get_bindings_for_keys(("a", "b"))
        return [binding.handler for binding in matches if binding.filter()]

    for global_enabled, binding_enabled in [
        (initial_global, True),
        (not initial_global, True),
        (True, False),
        (True, True),
        (False, True),
    ]:
        expected = [handler] if global_enabled and binding_enabled else []
        assert active_handlers() == expected
        assert active_handlers(prefix=True) == expected


def test_global_binding_preserves_attributes(handlers):
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.key_binding.key_bindings import GlobalOnlyKeyBindings

    bindings = KeyBindings()
    condition = Condition(lambda: True)
    save_before = lambda event: False
    bindings.add(
        "a",
        is_global=condition,
        eager=True,
        save_before=save_before,
        record_in_macro=False,
    )(handlers.global_handler)
    original = bindings.bindings[0]
    copied = GlobalOnlyKeyBindings(bindings).bindings[0]
    assert copied.keys == original.keys
    assert copied.handler is original.handler
    assert copied.is_global is condition
    assert copied.eager is original.eager
    assert copied.save_before is save_before
    assert copied.record_in_macro is original.record_in_macro
    assert copied.filter()


def test_global_binding_filter_changes_in_application(handlers):
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.layout import FormattedTextControl, HSplit

    enabled = False
    bindings = KeyBindings()
    bindings.add("x", is_global=Condition(lambda: enabled))(handlers.global_handler)
    focused = Window(FormattedTextControl("focused", focusable=True))
    unfocused = Window(
        FormattedTextControl("unfocused", focusable=True, key_bindings=bindings)
    )
    with create_pipe_input() as pipe_input:
        app = Application(
            layout=Layout(HSplit([focused, unfocused]), focused_element=focused),
            output=DummyOutput(),
            input=pipe_input,
        )
        app.layout.update_parents_relations()
        app.create_background_task = lambda coroutine, **kw: coroutine.close()
        with set_app(app):
            for enabled in (False, True, False, True):
                before = len(handlers.called)
                app.key_processor.feed(KeyPress("x", "x"))
                app.key_processor.process_keys()
                assert len(handlers.called) == before + int(enabled)
