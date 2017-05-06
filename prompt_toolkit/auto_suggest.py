"""
`Fish-style <http://fishshell.com/>`_  like auto-suggestion.

While a user types input in a certain buffer, suggestions are generated
(asynchronously.) Usually, they are displayed after the input. When the cursor
presses the right arrow and the cursor is at the end of the input, the
suggestion will be inserted.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from six import with_metaclass

from .filters import to_cli_filter

__all__ = (
    'Suggestion',
    'AutoSuggest',
    'AutoSuggestFromHistory',
    'ConditionalAutoSuggest',
)


class Suggestion(object):
    """
    Suggestion returned by an auto-suggest algorithm.

    :param text: The suggestion text.
    """
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return 'Suggestion(%s)' % self.text


class AutoSuggest(with_metaclass(ABCMeta, object)):
    """
    Base class for auto suggestion implementations.
    """
    @abstractmethod
    def get_suggestion(self, cli, buffer, document):
        """
        Return `None` or a :class:`.Suggestion` instance.

        We receive both ``buffer`` and ``document``. The reason is that auto
        suggestions are retrieved asynchronously. (Like completions.) The
        buffer text could be changed in the meantime, but ``document`` contains
        the buffer document like it was at the start of the auto suggestion
        call. So, from here, don't access ``buffer.text``, but use
        ``document.text`` instead.

        :param buffer: The :class:`~prompt_toolkit.buffer.Buffer` instance.
        :param document: The :class:`~prompt_toolkit.document.Document` instance.
        """


class AutoSuggestFromHistory(AutoSuggest):
    """
    Give suggestions based on the lines in the history.
    """
    def get_suggestion(self, cli, buffer, document):
        history = buffer.history

        # Consider only the last line for the suggestion.
        text = document.text.rsplit('\n', 1)[-1]

        # Only create a suggestion when this is not an empty line.
        if text.strip():
            # Find first matching line in history.
            for string in reversed(list(history)):
                for line in reversed(string.splitlines()):
                    if line.startswith(text):
                        return Suggestion(line[len(text):])


class ConditionalAutoSuggest(AutoSuggest):
    """
    Auto suggest that can be turned on and of according to a certain condition.
    """
    def __init__(self, auto_suggest, filter):
        assert isinstance(auto_suggest, AutoSuggest)

        self.auto_suggest = auto_suggest
        self.filter = to_cli_filter(filter)

    def get_suggestion(self, cli, buffer, document):
        if self.filter(cli):
            return self.auto_suggest.get_suggestion(cli, buffer, document)


class SimpleAutoSuggestCache(AutoSuggest):
    """
    Simple caching strategy for Auto-Suggestions.

    Will cache the previous auto suggestion and returns it immediately 
    if it's still valid for the current document. 

    This will ensure most of the time that the auto completion does not
    flicker while the user is typing.
    """


    def __init__(self, auto_suggest):
        self.auto_suggest = auto_suggest
        self._full_suggestion = ''


    def get_suggestion(self, cli, buffer, document):

        if self._full_suggestion.startswith(document.text):
            return Suggestion(self._full_suggestion[len(document.text):])

        suggestion =  self.auto_suggest.get_suggestion(cli, buffer, document) 
       
        if suggestion:
            self._full_suggestion = document.text + suggestion.text
        else:
            self._full_suggestion = ''

        return suggestion 




