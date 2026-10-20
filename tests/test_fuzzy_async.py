from __future__ import annotations

import asyncio
import threading

import pytest

from prompt_toolkit.completion import (
    CompleteEvent,
    Completer,
    Completion,
    FuzzyCompleter,
    ThreadedCompleter,
    WordCompleter,
)
from prompt_toolkit.document import Document


@pytest.mark.parametrize("enabled", [True, False])
def test_fuzzy_completer_uses_async_implementation(enabled):
    documents = []
    event = CompleteEvent(completion_requested=True)

    class AsyncCompleter(Completer):
        def get_completions(self, document, complete_event):
            raise AssertionError("Synchronous implementation must not be called")

        async def get_completions_async(self, document, complete_event):
            documents.append(document.text)
            assert complete_event is event
            for word in ["leopard", "cat", "oar", "dinosaur"]:
                yield Completion(word)

    async def collect():
        return [
            c
            async for c in FuzzyCompleter(
                AsyncCompleter(), enable_fuzzy=enabled
            ).get_completions_async(Document("oar"), event)
        ]

    completions = asyncio.run(collect())
    assert documents == ([""] if enabled else ["oar"])
    assert [c.text for c in completions] == (
        ["oar", "leopard", "dinosaur"]
        if enabled
        else ["leopard", "cat", "oar", "dinosaur"]
    )
    assert [c.start_position for c in completions] == ([-3] * 3 if enabled else [0] * 4)


def test_fuzzy_completer_keeps_threaded_completions_off_event_loop():
    main_thread = threading.get_ident()
    threads = []

    class RecordingCompleter(WordCompleter):
        def get_completions(self, document, complete_event):
            threads.append(threading.get_ident())
            return super().get_completions(document, complete_event)

    async def collect():
        completer = FuzzyCompleter(ThreadedCompleter(RecordingCompleter(["leopard"])))
        return [
            c.text
            async for c in completer.get_completions_async(
                Document("oar"), CompleteEvent()
            )
        ]

    assert asyncio.run(collect()) == ["leopard"]
    assert threads and all(thread != main_thread for thread in threads)


@pytest.mark.parametrize("enabled", [True, False])
def test_fuzzy_completer_closes_async_generator(enabled):
    closed = []

    class AsyncCompleter(Completer):
        def get_completions(self, document, complete_event):
            raise AssertionError("Synchronous implementation must not be called")

        async def get_completions_async(self, document, complete_event):
            try:
                yield Completion("leopard")
                if enabled:
                    raise ValueError("Completion failed")
                yield Completion("dinosaur")
            finally:
                closed.append(True)

    async def consume():
        generator = FuzzyCompleter(
            AsyncCompleter(), enable_fuzzy=enabled
        ).get_completions_async(Document("oar"), CompleteEvent())
        if enabled:
            with pytest.raises(ValueError, match="Completion failed"):
                await anext(generator)
        else:
            assert (await anext(generator)).text == "leopard"
            await generator.aclose()
        assert closed == [True]

    asyncio.run(consume())


@pytest.mark.parametrize("text", ["", "oar", "animals oar", "zz", "LEO"])
def test_fuzzy_completer_async_matches_sync(text):
    completer = FuzzyCompleter(WordCompleter(["leopard", "cat", "oar", "dinosaur"]))
    document = Document(text)
    event = CompleteEvent()

    async def collect():
        return [c async for c in completer.get_completions_async(document, event)]

    def describe(completions):
        return [(c.text, c.start_position, c.display) for c in completions]

    assert describe(asyncio.run(collect())) == describe(
        completer.get_completions(document, event)
    )


def test_fuzzy_completer_cancellation_closes_pending_generator():
    closed = []

    async def consume():
        started = asyncio.Event()

        class WaitingCompleter(Completer):
            def get_completions(self, document, complete_event):
                raise AssertionError("Synchronous implementation must not be called")

            async def get_completions_async(self, document, complete_event):
                try:
                    yield Completion("leopard")
                    started.set()
                    await asyncio.Event().wait()
                finally:
                    closed.append(True)

        generator = FuzzyCompleter(WaitingCompleter()).get_completions_async(
            Document("oar"), CompleteEvent()
        )
        task = asyncio.create_task(anext(generator))
        await asyncio.wait_for(started.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed == [True]

    asyncio.run(consume())
