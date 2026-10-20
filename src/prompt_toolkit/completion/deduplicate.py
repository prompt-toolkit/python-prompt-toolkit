from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Iterable

from prompt_toolkit.document import Document
from prompt_toolkit.eventloop import aclosing

from .base import CompleteEvent, Completer, Completion

__all__ = ["DeduplicateCompleter"]


class DeduplicateCompleter(Completer):
    """
    Wrapper around a completer that removes duplicates. Only the first unique
    completions are kept.

    Completions are considered to be a duplicate if they result in the same
    document text when they would be applied.
    """

    def __init__(self, completer: Completer) -> None:
        self.completer = completer

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        is_unique = _get_deduplicate_filter(document)

        for completion in self.completer.get_completions(document, complete_event):
            if is_unique(completion):
                yield completion

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion, None]:
        is_unique = _get_deduplicate_filter(document)

        async with aclosing(
            self.completer.get_completions_async(document, complete_event)
        ) as completions:
            async for completion in completions:
                if is_unique(completion):
                    yield completion


def _get_deduplicate_filter(document: Document) -> Callable[[Completion], bool]:
    # Keep track of the document strings we'd get after applying any completion.
    # Include the original text to exclude completions that have no effect.
    found_so_far = {document.text}

    def is_unique(completion: Completion) -> bool:
        text_if_applied = (
            document.text[: document.cursor_position + completion.start_position]
            + completion.text
            + document.text[document.cursor_position :]
        )

        if text_if_applied in found_so_far:
            return False

        found_so_far.add(text_if_applied)
        return True

    return is_unique
