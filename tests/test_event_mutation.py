import pytest

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.utils import Event


@pytest.mark.parametrize("fire_method", ["fire", "__call__"])
def test_self_removing_handler_does_not_skip_next(fire_method):
    sender = object()
    event = Event(sender)
    calls = []

    def once(value):
        calls.append(("once", value))
        event.remove_handler(once)

    def persistent(value):
        calls.append(("persistent", value))

    event += once
    event += persistent
    getattr(event, fire_method)()
    getattr(event, fire_method)()
    assert calls == [("once", sender), ("persistent", sender), ("persistent", sender)]


def test_handlers_added_during_dispatch_wait_until_next_event():
    event = Event(None)
    calls = []

    def added(sender):
        calls.append("added")

    def initial(sender):
        calls.append("initial")
        event.remove_handler(initial)
        event.add_handler(added)

    event += initial
    event.fire()
    assert calls == ["initial"]
    event.fire()
    assert calls == ["initial", "added"]


def test_removing_later_handler_applies_to_next_dispatch():
    event = Event(None)
    calls = []

    def first(sender):
        calls.append("first")
        event.remove_handler(second)

    def second(sender):
        calls.append("second")

    event += first
    event += second
    event.fire()
    event.fire()
    assert calls == ["first", "second", "first"]


def test_reentrant_event_uses_updated_handler_list():
    event = Event(None)
    calls = []

    def first(sender):
        calls.append("first")
        event.remove_handler(first)
        event.fire()

    def second(sender):
        calls.append("second")

    event += first
    event += second
    event.fire()
    assert calls == ["first", "second", "second"]


def test_buffer_text_change_reaches_persistent_listener():
    buffer = Buffer()
    changes = []

    def once(sender):
        sender.on_text_changed.remove_handler(once)

    def record(sender):
        changes.append(sender.text)

    buffer.on_text_changed += once
    buffer.on_text_changed += record
    buffer.text = "first"
    buffer.text = "second"
    assert changes == ["first", "second"]


def test_handler_exceptions_still_stop_dispatch():
    event = Event(None)
    calls = []

    def fail(sender):
        raise ValueError("handler failed")

    event += fail
    event += calls.append
    with pytest.raises(ValueError, match="handler failed"):
        event.fire()
    assert calls == []
