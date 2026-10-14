from __future__ import annotations

from contextlib import contextmanager

import pytest

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import set_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.key_binding.key_bindings import Binding, KeyBindings
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


def _save_true(event):
    return True


def _save_false(event):
    return False


class _FalsyCallable:
    """A save_before callable that is itself falsy."""

    def __bool__(self):
        return False

    def __call__(self, event):
        return False


def _source_binding(save_before, **kwargs):
    def handler(event):
        pass

    source_bindings = KeyBindings()
    source_bindings.add("a", save_before=save_before, **kwargs)(handler)
    return source_bindings.bindings[0]


def _add_binding(binding, **kwargs):
    kb = KeyBindings()
    result = kb.add("b", **kwargs)(binding)
    assert result is binding
    assert len(kb.bindings) == 1
    return kb.bindings[0]


@pytest.mark.parametrize("source_save_before", [_save_true, _save_false])
def test_add_binding_inherits_save_before_when_omitted(source_save_before):
    source = _source_binding(source_save_before)

    assert _add_binding(source).save_before is source_save_before
    assert _add_binding(source, save_before=None).save_before is source_save_before


@pytest.mark.parametrize(
    "source_save_before, explicit_save_before",
    [(_save_true, _save_false), (_save_false, _save_true)],
)
def test_add_binding_explicit_save_before_overrides(
    source_save_before, explicit_save_before
):
    source = _source_binding(source_save_before)

    added = _add_binding(source, save_before=explicit_save_before)

    assert added.save_before is explicit_save_before
    assert added.save_before(None) is explicit_save_before(None)
    # The source binding is not modified.
    assert source.save_before is source_save_before


def test_add_binding_falsy_save_before_callable_overrides():
    source = _source_binding(_save_true)
    falsy = _FalsyCallable()

    added = _add_binding(source, save_before=falsy)

    assert added.save_before is falsy
    assert source.save_before is _save_true


def test_add_binding_override_keeps_other_attributes():
    source_flag = [True]
    caller_flag = [True]
    source = _source_binding(
        _save_true,
        filter=Condition(lambda: source_flag[0]),
        record_in_macro=False,
    )

    added = _add_binding(
        source,
        save_before=_save_false,
        filter=Condition(lambda: caller_flag[0]),
        eager=True,
        is_global=True,
        record_in_macro=True,
    )

    assert added.handler is source.handler
    assert added.keys == ("b",)
    assert added.save_before is _save_false
    # Filters are still combined with "&".
    assert added.filter()
    source_flag[0] = False
    assert not added.filter()
    source_flag[0] = True
    caller_flag[0] = False
    assert not added.filter()
    # Eager and is_global are still combined with "|".
    assert added.eager()
    assert added.is_global()
    # record_in_macro is still inherited from the source binding.
    assert not added.record_in_macro()


def test_add_binding_twice_keeps_explicit_save_before():
    source = _source_binding(_save_true)
    first = _add_binding(source, save_before=_save_false)

    assert _add_binding(first).save_before is _save_false


def test_add_handler_save_before_defaults():
    def handler(event):
        pass

    kb = KeyBindings()
    assert kb.add("a")(handler) is handler
    kb.add("b", save_before=None)(handler)
    kb.add("c", save_before=_save_false)(handler)
    omitted, explicit_none, explicit = kb.bindings

    assert isinstance(omitted, Binding)
    assert omitted.save_before(None) is True
    assert explicit_none.save_before(None) is True
    assert explicit.save_before is _save_false
