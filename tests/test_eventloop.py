from __future__ import annotations

import asyncio
from collections import deque
from unittest.mock import Mock, patch

import pytest

from prompt_toolkit.eventloop.utils import call_soon_threadsafe


@pytest.mark.parametrize("postpone", [None, 1.0])
def test_call_soon_threadsafe_returns_cancellable_handle(postpone):
    loop = asyncio.new_event_loop()
    callback = Mock()
    try:
        handle = call_soon_threadsafe(callback, max_postpone_time=postpone, loop=loop)
        assert isinstance(handle, asyncio.Handle)
        handle.cancel()
        loop.run_until_complete(asyncio.sleep(0))
        callback.assert_not_called()
    finally:
        loop.close()


def test_cancel_after_postponement():
    loop = Mock(spec=asyncio.AbstractEventLoop)
    loop.get_debug.return_value = False
    pending = deque()
    loop.call_soon_threadsafe.side_effect = pending.append
    loop._ready = [object()]
    callback = Mock()
    with patch("prompt_toolkit.eventloop.utils.time.time", return_value=0):
        handle = call_soon_threadsafe(callback, max_postpone_time=1, loop=loop)
        pending.popleft()()
        callback.assert_not_called()
        assert len(pending) == 1
        assert isinstance(handle, asyncio.Handle)
        handle.cancel()
        pending.popleft()()
        callback.assert_not_called()
        assert not pending


@pytest.mark.parametrize("ready,now", [([], 0), ([object()], 2)])
def test_postponed_callback_runs_once(ready, now):
    loop = Mock(spec=asyncio.AbstractEventLoop)
    loop.get_debug.return_value = False
    pending = deque()
    loop.call_soon_threadsafe.side_effect = pending.append
    loop._ready = ready
    callback = Mock()
    with patch("prompt_toolkit.eventloop.utils.time.time", return_value=0) as clock:
        call_soon_threadsafe(callback, max_postpone_time=1, loop=loop)
        clock.return_value = now
        pending.popleft()()
    callback.assert_called_once_with()
    assert not pending


def test_loop_without_ready_attribute():
    loop = Mock(spec=asyncio.AbstractEventLoop)
    loop.get_debug.return_value = False
    pending = deque()
    loop.call_soon_threadsafe.side_effect = pending.append
    callback = Mock()
    call_soon_threadsafe(callback, max_postpone_time=1, loop=loop)
    pending.popleft()()
    callback.assert_called_once_with()
    assert not pending


@pytest.mark.parametrize("postpone", [None, 1.0])
def test_callback_runs_in_scheduling_context(postpone):
    from contextvars import ContextVar

    value = ContextVar("test_value", default="outside")
    loop = asyncio.new_event_loop()
    seen = []
    done = loop.create_future()

    def callback():
        seen.append(value.get())
        done.set_result(None)

    token = value.set("scheduled")
    try:
        call_soon_threadsafe(callback, max_postpone_time=postpone, loop=loop)
        value.reset(token)
        loop.run_until_complete(asyncio.sleep(0))
        loop.run_until_complete(done)
        assert seen == ["scheduled"]
    finally:
        loop.close()


@pytest.mark.parametrize("postpone", [None, 1.0])
def test_callback_exception_uses_loop_handler(postpone):
    loop = asyncio.new_event_loop()
    error = ValueError("callback error")
    contexts = []
    done = loop.create_future()

    def handle_exception(loop, context):
        contexts.append(context)
        done.set_result(None)

    loop.set_exception_handler(handle_exception)

    def callback():
        raise error

    try:
        call_soon_threadsafe(callback, max_postpone_time=postpone, loop=loop)
        loop.run_until_complete(asyncio.sleep(0))
        loop.run_until_complete(done)
        assert len(contexts) == 1
        assert contexts[0]["exception"] is error
    finally:
        loop.close()


@pytest.mark.parametrize("postpone", [None, 1.0])
def test_cancel_from_scheduling_thread(postpone):
    from threading import Thread

    loop = asyncio.new_event_loop()
    callback = Mock()
    errors = []

    def schedule_and_cancel():
        try:
            handle = call_soon_threadsafe(
                callback, max_postpone_time=postpone, loop=loop
            )
            handle.cancel()
        except BaseException as exc:
            errors.append(exc)

    try:
        thread = Thread(target=schedule_and_cancel)
        thread.start()
        thread.join()
        assert errors == []
        loop.run_until_complete(asyncio.sleep(0))
        callback.assert_not_called()
    finally:
        loop.close()


def test_uses_running_loop_when_not_specified():
    async def run():
        done = asyncio.get_running_loop().create_future()
        handle = call_soon_threadsafe(lambda: done.set_result(None))
        assert isinstance(handle, asyncio.Handle)
        await done

    asyncio.run(run())
