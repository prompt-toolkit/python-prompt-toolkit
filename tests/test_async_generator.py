from __future__ import annotations

from asyncio import run

from prompt_toolkit.eventloop import generator_to_async_generator


def _sync_generator():
    yield 1
    yield 10


def test_generator_to_async_generator():
    """
    Test conversion of sync to async generator.
    This should run the synchronous parts in a background thread.
    """
    async_gen = generator_to_async_generator(_sync_generator)

    items = []

    async def consume_async_generator():
        async for item in async_gen:
            items.append(item)

    # Run the event loop until all items are collected.
    run(consume_async_generator())
    assert items == [1, 10]
