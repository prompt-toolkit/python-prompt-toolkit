from typing import Iterable, Optional

from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.formatted_text import AnyFormattedText

from .base import _T, ProgressBar, ProgressBarCounter


class DummyProgressBar(ProgressBar):
    """
    When no :class:`.ProgressBar` is running,
    :func:`.get_app` will run an instance of this :class:`.DummyApplication` instead.
    """

    def __enter__(self) -> None:
        raise NotImplementedError("A DummyProgressBar is not supposed to be used.")

    def __exit__(self, *a: object) -> None:
        raise NotImplementedError("A DummyProgressBar is not supposed to be used.")

    def __call__(
        self,
        data: Optional[Iterable[_T]] = None,
        label: AnyFormattedText = "",
        remove_when_done: FilterOrBool = False,
        total: Optional[int] = None,
    ) -> None:
        return DummyProgressBarCounter()

    def invalidate(self) -> None:
        raise NotImplementedError


class DummyProgressBarCounter(ProgressBarCounter[None]):
    """
    An individual counter (A progress bar can have multiple counters).
    """

    def __iter__(self) -> None:
        raise NotImplementedError(
            "A DummyProgressBarCounter is not supposed to be iterated."
        )

    def item_completed(self) -> None:
        raise NotImplementedError(
            "A DummyProgressBarCounter is not supposed to be incremented."
        )
