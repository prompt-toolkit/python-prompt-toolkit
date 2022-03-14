from typing import List

import py

from prompt_toolkit.eventloop import get_event_loop
from prompt_toolkit.history import (
    FileHistory,
    History,
    InMemoryHistory,
    ThreadedHistory,
)


def _call_history_load(history: History) -> List[str]:
    """
    Helper: Call the history "load" method and return the result as a list of strings.
    """
    result: List[str] = []

    async def call_load() -> None:
        async for item in history.load():
            result.append(item)

    get_event_loop().run_until_complete(call_load())
    return result


def test_in_memory_history() -> None:
    history = InMemoryHistory()
    history.append_string("hello")
    history.append_string("world")

    # Newest should yield first.
    assert _call_history_load(history) == ["world", "hello"]

    # Test another call.
    assert _call_history_load(history) == ["world", "hello"]

    history.append_string("test3")
    assert _call_history_load(history) == ["test3", "world", "hello"]

    # Passing history as a parameter.
    history2 = InMemoryHistory(["abc", "def"])
    assert _call_history_load(history2) == ["def", "abc"]


def test_file_history(tmpdir: py.path.local) -> None:
    histfile = tmpdir.join("history")

    history = FileHistory(str(histfile))

    history.append_string("hello")
    history.append_string("world")

    # Newest should yield first.
    assert _call_history_load(history) == ["world", "hello"]

    # Test another call.
    assert _call_history_load(history) == ["world", "hello"]

    history.append_string("test3")
    assert _call_history_load(history) == ["test3", "world", "hello"]

    # Create another history instance pointing to the same file.
    history2 = FileHistory(str(histfile))
    assert _call_history_load(history2) == ["test3", "world", "hello"]


def test_threaded_file_history(tmpdir: py.path.local) -> None:
    histfile = tmpdir.join("history")

    history = ThreadedHistory(FileHistory(str(histfile)))

    history.append_string("hello")
    history.append_string("world")

    # Newest should yield first.
    assert _call_history_load(history) == ["world", "hello"]

    # Test another call.
    assert _call_history_load(history) == ["world", "hello"]

    history.append_string("test3")
    assert _call_history_load(history) == ["test3", "world", "hello"]

    # Create another history instance pointing to the same file.
    history2 = ThreadedHistory(FileHistory(str(histfile)))
    assert _call_history_load(history2) == ["test3", "world", "hello"]


def test_threaded_in_memory_history() -> None:
    # Threaded in memory history is not useful. But testing it anyway, just to
    # see whether everything plays nicely together.
    history = ThreadedHistory(InMemoryHistory())
    history.append_string("hello")
    history.append_string("world")

    # Newest should yield first.
    assert _call_history_load(history) == ["world", "hello"]

    # Test another call.
    assert _call_history_load(history) == ["world", "hello"]

    history.append_string("test3")
    assert _call_history_load(history) == ["test3", "world", "hello"]

    # Passing history as a parameter.
    history2 = ThreadedHistory(InMemoryHistory(["abc", "def"]))
    assert _call_history_load(history2) == ["def", "abc"]
