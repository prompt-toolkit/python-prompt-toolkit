"""
Implementation for async generators.
"""
from asyncio import Queue, get_event_loop
from typing import AsyncGenerator, Callable, Iterable, TypeVar, Union

from .utils import run_in_executor_with_context

__all__ = [
    "generator_to_async_generator",
]


_T = TypeVar("_T")


class _Done:
    pass


async def generator_to_async_generator(
    get_iterable: Callable[[], Iterable[_T]]
) -> AsyncGenerator[_T, None]:
    """
    Turn a generator or iterable into an async generator.

    This works by running the generator in a background thread.

    :param get_iterable: Function that returns a generator or iterable when
        called.
    """
    quitting = False
    _done = _Done()
    q: Queue[Union[_T, _Done]] = Queue()
    loop = get_event_loop()

    def runner() -> None:
        """
        Consume the generator in background thread.
        When items are received, they'll be pushed to the queue.
        """
        try:
            for item in get_iterable():
                # When this async generator was cancelled (closed), stop this
                # thread.
                if quitting:
                    break

                loop.call_soon_threadsafe(q.put_nowait, item)

        finally:
            loop.call_soon_threadsafe(q.put_nowait, _done)

    # Start background thread.
    runner_f = run_in_executor_with_context(runner)

    try:
        while True:
            item = await q.get()
            if isinstance(item, _Done):
                break
            else:
                yield item
    finally:
        # When this async generator is closed (GeneratorExit exception, stop
        # the background thread as well. - we don't need that anymore.)
        quitting = True

        # Wait for the background thread to finish. (should happen right after
        # the next item is yielded). If we don't do this, and the event loop
        # gets closed before the runner is done, then we'll get a
        # `RuntimeError: Event loop is closed` exception printed to stdout that
        # we can't handle.
        await runner_f
