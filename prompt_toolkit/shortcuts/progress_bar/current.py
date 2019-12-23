import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator, Optional

try:
    from contextvars import ContextVar
except ImportError:
    from prompt_toolkit.eventloop.dummy_contextvars import ContextVar  # type: ignore

if TYPE_CHECKING:
    from .base import ProgressBar, ProgressBarCounter

__all__ = ["get_progress_bar", "set_progress_bar", "get_counter", "set_counter"]


class ProgressBarSession:
    def __init__(self) -> None:
        self.progress_bar: Optional["ProgressBar"] = None
        self.counter: Optional["ProgressBarCounter"] = None

    def __repr__(self) -> str:
        return "ProgressBarSession(progress_bar=%r, counter=%r)" % (
            self.progress_bar,
            self.counter,
        )


_current_pb_session: ContextVar["ProgressBarSession"] = ContextVar(
    "_current_pb_session", default=ProgressBarSession()
)


def get_progress_bar() -> "ProgressBar":
    session = _current_pb_session.get()
    if session.progress_bar is not None:
        return session.progress_bar

    from .dummy import DummyProgressBar

    return DummyProgressBar()


@contextmanager
def set_progress_bar(progress_bar: "ProgressBar") -> Generator[None, None, None]:
    session = _current_pb_session.get()

    previous_br = session.progress_bar
    session.progress_bar = progress_bar
    try:
        yield
    finally:
        session.progress_bar = previous_br


def get_counter() -> "ProgressBarCounter":
    session = _current_pb_session.get()
    if session.counter is not None:
        return session.counter

    from .dummy import DummyProgressBarCounter

    return DummyProgressBarCounter()


@contextmanager
def set_counter(counter: "ProgressBarCounter") -> Generator[None, None, None]:
    session = _current_pb_session.get()

    previous_counter = session.counter
    session.counter = counter
    try:
        yield
    finally:
        session.counter = previous_counter
