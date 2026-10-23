from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

import prompt_toolkit.application.application as application_module
import prompt_toolkit.eventloop.inputhook as inputhook_module
from prompt_toolkit.application.application import Application
from prompt_toolkit.eventloop.inputhook import InputHookContext, InputHookSelector
from prompt_toolkit.output import DummyOutput


class StubSelector:
    def __init__(self) -> None:
        self.closed = False

    def select(self, timeout: float | None = None) -> list[tuple[object, int]]:
        return []

    def close(self) -> None:
        self.closed = True

    def get_map(self) -> dict[object, object]:
        return {}


def test_inputhook_selector_handles_large_pipe_descriptors(monkeypatch):
    writes = []
    reads = []

    def read(fd, size):
        reads.append((fd, size))
        return b"x"

    fake_os = SimpleNamespace(
        pipe=lambda: (1024, 1025),
        write=lambda fd, data: writes.append((fd, data)) or len(data),
        read=read,
        close=lambda fd: None,
    )
    monkeypatch.setattr(inputhook_module, "os", fake_os)
    monkeypatch.setattr(
        inputhook_module,
        "select",
        SimpleNamespace(select=lambda *args: pytest.fail("select.select was called")),
        raising=False,
    )
    monkeypatch.setattr(
        inputhook_module, "get_running_loop", lambda: SimpleNamespace(_ready=[])
    )

    def inputhook(context: InputHookContext) -> None:
        deadline = time.monotonic() + 1
        while not context.input_is_ready():
            if time.monotonic() >= deadline:
                raise AssertionError("selector did not become ready")
            time.sleep(0.001)

    selector = InputHookSelector(StubSelector(), inputhook)

    try:
        assert selector.select(timeout=0) == []
        assert writes == [(1025, b"x")]
        assert reads == [(1024, 1024)]
    finally:
        selector.close()


@pytest.mark.parametrize("pipe_fds", [(0, 1), (1024, 1025)])
def test_inputhook_selector_close_handles_pipe_descriptors(monkeypatch, pipe_fds):
    closed = []
    fake_os = SimpleNamespace(pipe=lambda: pipe_fds, close=closed.append)
    monkeypatch.setattr(inputhook_module, "os", fake_os)
    selector = InputHookSelector(StubSelector(), lambda context: None)

    selector.close()
    selector.close()

    assert closed == list(pipe_fds)


@pytest.mark.parametrize("error", [KeyboardInterrupt, EOFError])
def test_application_run_closes_inputhook_loop_after_interrupt(monkeypatch, error):
    run_coro = object()
    shutdown_coro = object()
    calls = []

    class StubLoop:
        def run_until_complete(self, coro):
            if coro is run_coro:
                raise error
            assert coro is shutdown_coro
            calls.append("shutdown")

        def shutdown_asyncgens(self):
            return shutdown_coro

        def close(self):
            calls.append("close")

    loop = StubLoop()
    app = Application(output=DummyOutput())
    app.run_async = lambda **kwargs: run_coro
    monkeypatch.setattr(
        application_module, "new_eventloop_with_inputhook", lambda inputhook: loop
    )

    with pytest.raises(error):
        app.run(inputhook=lambda context: None)

    assert calls == ["shutdown", "close"]
