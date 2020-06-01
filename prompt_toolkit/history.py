"""
Implementations for the history of a `Buffer`.

NOTE: Notice that there is no `DynamicHistory`. This doesn't work well, because
      the `Buffer` needs to be able to attach an event handler to the event
      when a history entry is loaded. This loading can be done asynchronously
      and making the history swappable would probably break this.
"""
import datetime
import os
from abc import ABCMeta, abstractmethod
from threading import Thread
from typing import Callable, Iterable, List, Optional
import asyncio
import time

__all__ = [
    "History",
    "ThreadedHistory",
    "DummyHistory",
    "FileHistory",
    "InMemoryHistory",
]


class History(metaclass=ABCMeta):
    """
    Base ``History`` class.

    This also includes abstract methods for loading/storing history.
    """

    def __init__(self) -> None:
        # In memory storage for strings.
        self._loaded = False
        self._loaded_strings: List[str] = []

    #
    # Methods expected by `Buffer`.
    #

    def load(
        self,
        item_loaded_callback: Callable[[str], None],
        event_loop: asyncio.BaseEventLoop = None,
    ) -> None:
        """
        Load the history and call the callback for every entry in the history.
        This one assumes the callback is only called from same thread as `Buffer` is using.

        See `ThreadedHistory` for another way.
        """
        if self._loaded:
            for item in self._loaded_strings[::-1]:
                item_loaded_callback(item)
            return

        try:
            for item in self.load_history_strings():
                self._loaded_strings.insert(0, item)
                item_loaded_callback(item)
        finally:
            self._loaded = True

    def get_strings(self) -> List[str]:
        """
        Get the strings from the history that are loaded so far.
        """
        return self._loaded_strings

    def append_string(self, string: str) -> None:
        " Add string to the history. "
        self._loaded_strings.append(string)
        self.store_string(string)

    #
    # Implementation for specific backends.
    #

    @abstractmethod
    def load_history_strings(self) -> Iterable[str]:
        """
        This should be a generator that yields `str` instances.

        It should yield the most recent items first, because they are the most
        important. (The history can already be used, even when it's only
        partially loaded.)
        """
        while False:
            yield

    @abstractmethod
    def store_string(self, string: str) -> None:
        """
        Store the string in persistent storage.
        """


class ThreadedHistory(History):
    """
    Wrapper that runs the `load_history_strings` generator in a thread.

    Use this to increase the start-up time of prompt_toolkit applications.
    History entries are available as soon as they are loaded. We don't have to
    wait for everything to be loaded.
    """

    def __init__(self, history: History) -> None:
        self.history = history
        self._load_thread: Optional[Thread] = None
        self._item_loaded_callbacks: List[Callable[[str], None]] = []
        super().__init__()

    def load(self, item_loaded_callback: Callable[[str], None]) -> None:
        """Collect the history strings but run the callback in the event loop.

        That's the only way to avoid multitasking hazards if the loaded history is large.
        Callback into `Buffer` tends to get working_index all tangled up.

        Caller of ThreadedHistory must ensure that the prompt ends up running on the same
        event loop as we create here.
        """

        self._item_loaded_callbacks.append(item_loaded_callback)

        def call_all_callbacks(item: str) -> None:
            for cb in self._item_loaded_callbacks:
                cb(item)

        if self._loaded:  # ugly reference to base class internal...
            for item in self._loaded_strings[::-1]:
                call_all_callbacks(item)
            return

        # Start the load thread, if we don't have a thread yet.
        if not self._load_thread:

            event_loop = asyncio.get_event_loop()

            self._load_thread = Thread(
                target=self.bg_loader, args=(call_all_callbacks, event_loop)
            )
            self._load_thread.daemon = True
            self._load_thread.start()

    def bg_loader(
        self,
        item_loaded_callback: Callable[[str], None],
        event_loop: asyncio.BaseEventLoop,
    ) -> None:
        """
        Load the history and schedule the callback for every entry in the history.
        TODO: extend the callback so it can take a batch of lines in one event_loop dispatch.
        """

        # heuristic: don't flood the event loop with callback events when prompt is just starting up.
        # let the first 10000 or so history lines go through, then sleep for 3 sec, then continue the flood.
        # all numbers tuned on my PC.  YMMV.

        burst_countdown = 10000
        try:
            for item in self.load_history_strings():
                self._loaded_strings.insert(0, item)    # slowest way to add an element to a list known to man.
                event_loop.call_soon_threadsafe(item_loaded_callback, item)  # expensive way to dispatch single line.
                if burst_countdown:
                    burst_countdown -= 1
                    if burst_countdown == 0:
                        time.sleep(3.0)
        finally:
            self._loaded = True

    def __repr__(self) -> str:
        return "ThreadedHistory(%r)" % (self.history,)

    # All of the following are proxied to `self.history`.

    def load_history_strings(self) -> Iterable[str]:
        return self.history.load_history_strings()

    def store_string(self, string: str) -> None:
        self.history.store_string(string)


class InMemoryHistory(History):
    """
    :class:`.History` class that keeps a list of all strings in memory.
    """

    def load_history_strings(self) -> Iterable[str]:
        return []

    def store_string(self, string: str) -> None:
        pass


class DummyHistory(History):
    """
    :class:`.History` object that doesn't remember anything.
    """

    def load_history_strings(self) -> Iterable[str]:
        return []

    def store_string(self, string: str) -> None:
        pass

    def append_string(self, string: str) -> None:
        # Don't remember this.
        pass


class FileHistory(History):
    """
    :class:`.History` class that stores all strings in a file.
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename
        super(FileHistory, self).__init__()

    def load_history_strings(self) -> Iterable[str]:
        strings: List[str] = []
        lines: List[str] = []

        def add() -> None:
            if lines:
                # Join and drop trailing newline.
                string = "".join(lines)[:-1]

                strings.append(string)

        if os.path.exists(self.filename):
            with open(self.filename, "rb") as f:
                for line_bytes in f:
                    line = line_bytes.decode("utf-8")

                    if line.startswith("+"):
                        lines.append(line[1:])
                    else:
                        add()
                        lines = []

                add()

        # Reverse the order, because newest items have to go first.
        return reversed(strings)

    def store_string(self, string: str) -> None:
        # Save to file.
        with open(self.filename, "ab") as f:

            def write(t: str) -> None:
                f.write(t.encode("utf-8"))

            write("\n# %s\n" % datetime.datetime.now())
            for line in string.split("\n"):
                write("+%s\n" % line)
