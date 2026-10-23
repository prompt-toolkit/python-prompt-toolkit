from __future__ import annotations

import errno
import os
import selectors
import sys
import time
from types import SimpleNamespace

import pytest

from prompt_toolkit.application import application
from prompt_toolkit.eventloop import inputhook
from prompt_toolkit.eventloop.inputhook import InputHookSelector
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import PromptSession


def test_inputhook_selector_close_is_idempotent() -> None:
    selector = InputHookSelector(selectors.DefaultSelector(), lambda context: None)

    selector.close()
    selector.close()


@pytest.mark.skipif(
    sys.platform == "win32" or not hasattr(inputhook.select, "poll"),
    reason="requires POSIX poll support",
)
def test_inputhook_selector_supports_high_file_descriptors(monkeypatch) -> None:
    # select.select() rejects descriptors >= FD_SETSIZE (usually 1024), even
    # when the platform's default selector supports them.
    fds: list[int] = []
    selector: InputHookSelector | None = None
    try:
        try:
            for _ in range(1050):
                fds.append(os.open(os.devnull, os.O_RDONLY))
        except OSError as e:
            if e.errno == errno.EMFILE:
                pytest.skip("not enough file descriptors to exercise FD_SETSIZE")
            raise

        selector = InputHookSelector(selectors.DefaultSelector(), lambda context: None)
        if selector._r < 1024:
            pytest.skip("the wake descriptor is below FD_SETSIZE")

        monkeypatch.setattr(
            inputhook,
            "get_running_loop",
            lambda: SimpleNamespace(_ready=[]),
        )
        assert selector.select(timeout=0) == []
    finally:
        if selector is not None:
            selector.close()
        for fd in fds:
            os.close(fd)


@pytest.mark.parametrize(
    ("key", "exception"),
    [("\x03", KeyboardInterrupt), ("\x04", EOFError)],
)
def test_application_closes_inputhook_loop_after_interrupt(
    monkeypatch, key, exception
) -> None:
    loops = []
    create_loop = application.new_eventloop_with_inputhook

    def record_loop(input_hook):
        loop = create_loop(input_hook)
        loops.append(loop)
        return loop

    monkeypatch.setattr(application, "new_eventloop_with_inputhook", record_loop)

    def wait_until_ready(context) -> None:
        while not context.input_is_ready():
            time.sleep(0.001)

    with create_pipe_input() as pipe_input:
        session = PromptSession(input=pipe_input, output=DummyOutput())
        pipe_input.send_text(key)
        with pytest.raises(exception):
            session.prompt(inputhook=wait_until_ready)

    assert len(loops) == 1
    assert loops[0].is_closed()
