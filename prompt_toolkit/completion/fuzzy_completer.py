from __future__ import unicode_literals

import re
from six import string_types
from prompt_toolkit.completion import Completer, Completion

__all__ = [
    'FuzzyCompleter',
]


class FuzzyCompleter(Completer):
    """
    Fuzzy completion on a list of words.

    :param words: List of words or callable that returns a list of words.
    :param meta_dict: Optional dict mapping words to their meta-information.
    :param WORD: When True, use WORD characters.
    :param sort_results: Boolean to determine whether to sort the results (default: True).

    Fuzzy algorithm is based on this post: https://blog.amjith.com/fuzzyfinder-in-10-lines-of-python
    """
    def __init__(self, words, meta_dict=None, WORD=False, sort_results=True):
        assert callable(words) or all(isinstance(w, string_types) for w in words)

        self.words = words
        self.meta_dict = meta_dict or {}
        self.sort_results = sort_results
        self.WORD = WORD

    def get_completions(self, document, complete_event):
        # Get list of words.
        words = self.words
        if callable(words):
            words = words()

        word_before_cursor = document.get_word_before_cursor(WORD=self.WORD)

        suggestions = []
        pat = '.*?'.join(map(re.escape, word_before_cursor))
        pat = '(?=({0}))'.format(pat)   # lookahead regex to manage overlapping matches
        regex = re.compile(pat, re.IGNORECASE)
        for item in words:
            r = list(regex.finditer(item))
            if r:
                best = min(r, key=lambda x: len(x.group(1)))   # find shortest match
                suggestions.append((len(best.group(1)), best.start(), item))

        if self.sort_results:
            results = (z[-1] for z in sorted(suggestions))
        else:
            results = (z[-1] for z in sorted(suggestions, key=lambda x: x[:-1]))

        for result in results:
            display_meta = self.meta_dict.get(result, '')
            yield Completion(result, -len(word_before_cursor), display_meta=display_meta)
