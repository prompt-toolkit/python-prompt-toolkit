#!/usr/bin/env python
"""
Nestedcompleter for completion of hierarchical data structures, with meta.
"""
from dataclasses import dataclass
from typing import Iterable

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.completion.word_completer import WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import AnyFormattedText

__all__ = ["NestedMetaData", "NestedMetaCompleter"]


@dataclass
class NestedMetaData:
    key: str
    meta: AnyFormattedText
    data: Iterable["NestedMetaCompleter"]


class NestedMetaCompleter(Completer):
    def __init__(
        self, data: Iterable["NestedMetaData"], ignore_case: bool = True
    ) -> None:

        self.data = data
        self.ignore_case = ignore_case

    def __repr__(self) -> str:
        return "NestedMetaCompleter(%r, ignore_case=%r)" % (self.data, self.ignore_case)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        # If there is a space, check for the first term, and use a
        # subcompleter.
        text = document.text_before_cursor.lstrip()
        if " " in text:
            # Split document.
            first_term = text.split()[0]
            _completers = [item.data for item in self.data if item.key == first_term]
            if not _completers:
                return
            # If we have a sub completer, use this for the completions.
            completers = _completers[0]
            remaining_text = text[len(first_term) :].lstrip()
            stripped_len = len(document.text_before_cursor) - len(text)
            move_cursor = len(text) - len(remaining_text) + stripped_len

            new_document = Document(
                remaining_text,
                cursor_position=document.cursor_position - move_cursor,
            )
            for completer in completers:
                for c in completer.get_completions(new_document, complete_event):
                    yield c

        # No space in the input: behave exactly like `WordCompleter`.
        else:
            w_completer = WordCompleter(
                [item.key for item in self.data],
                ignore_case=False,
                meta_dict={item.key: item.meta for item in self.data},
            )
            for c in w_completer.get_completions(document, complete_event):
                yield c
