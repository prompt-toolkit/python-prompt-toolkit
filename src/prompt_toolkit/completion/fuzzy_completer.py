from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import NamedTuple

from prompt_toolkit.document import Document
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples

from .base import CompleteEvent, Completer, Completion
from .word_completer import WordCompleter

__all__ = [
    "FuzzyCompleter",
    "FuzzyWordCompleter",
]


class FuzzyCompleter(Completer):
    """
    Fuzzy completion.
    This wraps any other completer and turns it into a fuzzy completer.

    If the list of words is: ["leopard" , "gorilla", "dinosaur", "cat", "bee"]
    Then trying to complete "oar" would yield "leopard" and "dinosaur", but not
    the others, because they match the regular expression 'o.*a.*r'.
    Similar, in another application "djm" could expand to "django_migrations".

    The results are sorted by relevance, which is defined as the start position
    and the length of the match.

    Notice that this is not really a tool to work around spelling mistakes,
    like what would be possible with difflib. The purpose is rather to have a
    quicker or more intuitive way to filter the given completions, especially
    when many completions have a common prefix.

    Fuzzy algorithm is based on this post:
    https://blog.amjith.com/fuzzyfinder-in-10-lines-of-python

    :param completer: A :class:`~.Completer` instance.
    :param WORD: When True, use WORD characters.
    :param pattern: Regex pattern which selects the characters before the
        cursor that are considered for the fuzzy matching.
    :param enable_fuzzy: (bool or `Filter`) Enabled the fuzzy behavior. For
        easily turning fuzzyness on or off according to a certain condition.
    """

    def __init__(
        self,
        completer: Completer,
        WORD: bool = False,
        pattern: str | None = None,
        enable_fuzzy: FilterOrBool = True,
    ) -> None:
        assert pattern is None or pattern.startswith("^")

        self.completer = completer
        self.pattern = pattern
        self.WORD = WORD
        self.pattern = pattern
        self.enable_fuzzy = to_filter(enable_fuzzy)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        if self.enable_fuzzy():
            return self._get_fuzzy_completions(document, complete_event)
        else:
            return self.completer.get_completions(document, complete_event)

    def _get_pattern(self) -> str:
        if self.pattern:
            return self.pattern
        if self.WORD:
            return r"[^\s]+"
        return "^[a-zA-Z0-9_]*"

    def _get_fuzzy_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        word_before_cursor = document.get_word_before_cursor(
            pattern=re.compile(self._get_pattern())
        )

        # Get completions
        document2 = Document(
            text=document.text[: document.cursor_position - len(word_before_cursor)],
            cursor_position=document.cursor_position - len(word_before_cursor),
        )

        inner_completions = list(
            self.completer.get_completions(document2, complete_event)
        )

        fuzzy_matches: list[_FuzzyMatch] = []

        if word_before_cursor == "":
            # If word before the cursor is an empty string, consider all
            # completions, without filtering everything with an empty regex
            # pattern.
            fuzzy_matches = [_FuzzyMatch(0, 0, compl) for compl in inner_completions]
        else:
            # Match each character separately to retain re.IGNORECASE's Unicode
            # semantics without building a backtracking subsequence regex.
            patterns = [
                re.compile(re.escape(c), re.IGNORECASE) for c in word_before_cursor
            ]
            for compl in inner_completions:
                bounds = _find_fuzzy_match(compl.text, patterns)
                if bounds is not None:
                    start, length = bounds
                    fuzzy_matches.append(_FuzzyMatch(length, start, compl))

            def sort_key(fuzzy_match: _FuzzyMatch) -> tuple[int, int]:
                "Sort by start position, then by the length of the match."
                return fuzzy_match.start_pos, fuzzy_match.match_length

            fuzzy_matches = sorted(fuzzy_matches, key=sort_key)

        for match in fuzzy_matches:
            # Include these completions, but set the correct `display`
            # attribute and `start_position`.
            yield Completion(
                text=match.completion.text,
                start_position=match.completion.start_position
                - len(word_before_cursor),
                # We access to private `_display_meta` attribute, because that one is lazy.
                display_meta=match.completion._display_meta,
                display=self._get_display(match, word_before_cursor),
                style=match.completion.style,
            )

    def _get_display(
        self, fuzzy_match: _FuzzyMatch, word_before_cursor: str
    ) -> AnyFormattedText:
        """
        Generate formatted text for the display label.
        """

        def get_display() -> AnyFormattedText:
            m = fuzzy_match
            word = m.completion.text

            if m.match_length == 0:
                # No highlighting when we have zero length matches (no input text).
                # In this case, use the original display text (which can include
                # additional styling or characters).
                return m.completion.display

            result: StyleAndTextTuples = []

            # Text before match.
            result.append(("class:fuzzymatch.outside", word[: m.start_pos]))

            # The match itself.
            characters = list(word_before_cursor)

            for c in word[m.start_pos : m.start_pos + m.match_length]:
                classname = "class:fuzzymatch.inside"
                if characters and c.lower() == characters[0].lower():
                    classname += ".character"
                    del characters[0]

                result.append((classname, c))

            # Text after match.
            result.append(
                ("class:fuzzymatch.outside", word[m.start_pos + m.match_length :])
            )

            return result

        return get_display()


class FuzzyWordCompleter(Completer):
    """
    Fuzzy completion on a list of words.

    (This is basically a `WordCompleter` wrapped in a `FuzzyCompleter`.)

    :param words: List of words or callable that returns a list of words.
    :param meta_dict: Optional dict mapping words to their meta-information.
    :param WORD: When True, use WORD characters.
    """

    def __init__(
        self,
        words: Sequence[str] | Callable[[], Sequence[str]],
        meta_dict: Mapping[str, AnyFormattedText] | None = None,
        WORD: bool = False,
    ) -> None:
        self.words = words
        self.meta_dict = meta_dict or {}
        self.WORD = WORD

        self.word_completer = WordCompleter(
            words=self.words, WORD=self.WORD, meta_dict=self.meta_dict
        )

        self.fuzzy_completer = FuzzyCompleter(self.word_completer, WORD=self.WORD)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        return self.fuzzy_completer.get_completions(document, complete_event)


class _FuzzyMatch(NamedTuple):
    match_length: int
    start_pos: int
    completion: Completion


def _find_fuzzy_match(
    text: str, patterns: list[re.Pattern[str]]
) -> tuple[int, int] | None:
    """Find the leftmost, shortest subsequence in O(len(text) * len(patterns))."""
    if not any(pattern.fullmatch("\n") for pattern in patterns):
        # Within one line, taking each character's earliest occurrence gives
        # the shortest match at the earliest start. If it cannot finish, no
        # later start on that line can finish either.
        offset = 0
        for line in text.split("\n"):
            first = patterns[0].search(line)
            if first is not None:
                end = first.end()
                for pattern in patterns[1:]:
                    match = pattern.search(line, end)
                    if match is None:
                        break
                    end = match.end()
                else:
                    return offset + first.start(), end - first.start()
            offset += len(line) + 1
        return None

    # Custom patterns can select queries containing literal newlines.
    # ends[i] is the exclusive end of the earliest matching suffix for
    # patterns[i:] to the right of the current position. Scan backwards so a
    # character is never consumed twice. Earlier matches replace later ones.
    ends: list[int | None] = [None] * len(patterns)
    result = None
    for position in range(len(text) - 1, -1, -1):
        char = text[position]
        for i, pattern in enumerate(patterns):
            if pattern.fullmatch(char):
                ends[i] = position + 1 if i == len(patterns) - 1 else ends[i + 1]
                suffix_end = ends[i]
                if i == 0 and suffix_end is not None:
                    result = (position, suffix_end - position)
            elif char == "\n":
                # The old regex's .*? gaps could not skip a newline. Literal
                # newline characters in a custom query can still match one.
                ends[i] = None
    return result
