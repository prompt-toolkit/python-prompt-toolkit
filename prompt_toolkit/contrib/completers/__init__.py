from __future__ import unicode_literals

from six import string_types
from prompt_toolkit.completion import Completer, Completion

import os



class WordCompleter(Completer):
    def __init__(self, words, ignore_case=False, meta_dict=None):
        self.words = list(words)
        self.ignore_case = ignore_case
        self.meta_dict = meta_dict or {}
        assert all(isinstance(w, string_types) for w in self.words)

        if ignore_case:
            self.words = [w.lower() for w in self.words]

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor()

        if self.ignore_case:
            word_before_cursor = word_before_cursor.lower()

        for a in self.words:
            if a.startswith(word_before_cursor):
                display_meta = self.meta_dict.get(a, '')
                yield Completion(a, -len(word_before_cursor), display_meta=display_meta)


class PathCompleter(Completer):
    """
    Complete for Path variables.
    """
    def __init__(self, include_files=True):
        self.include_files = include_files

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        try:
            directory = os.path.dirname(text) or '.'
            prefix = os.path.basename(text)

            for filename in os.listdir(directory):
                if filename.startswith(prefix):
                    completion = filename[len(prefix):]
                    full_name = os.path.join(directory, filename)

                    if not os.path.isdir(full_name):
                        if not self.include_files:
                            continue

                    meta = self._get_meta(full_name)
                    yield Completion(completion, 0, display=filename, display_meta=meta)
        except OSError:
            pass

    def _get_meta(self, full_name):
        """
        Return meta display string for file/directory.
        """
        if os.path.isdir(full_name):
            return 'Directory'
        elif os.path.isfile(full_name):
            return 'File'
        elif os.path.islink(full_name):
            return 'Link'
        else:
            return ''
