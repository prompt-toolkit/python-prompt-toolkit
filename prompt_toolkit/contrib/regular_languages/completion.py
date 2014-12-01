"""
Completer for a regular grammar.
"""
from __future__ import unicode_literals

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from .compiler import _CompiledGrammar
from .grammar import Variable

__all__ = (
    'GrammarCompleter',
)


class GrammarCompleter(Completer):
    """
    Completer for a regular grammar.
    This `GrammarCompleter` takes the completers as defined in the variables of
    a grammar. It can be used like any other completer.
    """
    def __init__(self, compiled_grammar):
        assert isinstance(compiled_grammar, _CompiledGrammar)
        self.compiled_grammar = compiled_grammar

    def get_completions(self, document, complete_event):
        m = self.compiled_grammar.match_prefix(document.text_before_cursor)

        if m:
            completions = self._remove_duplicates(
                self._get_completions_for_match(m, complete_event))

            for c in completions:
                yield c

    def _get_completions_for_match(self, match, complete_event):
        """
        Yield all the possible completions for this input string.
        (The completer assumes that the cursor position was at the end of the
        input string.)
        """
        for node, start, stop in match.end_nodes():
            if isinstance(node, Variable) and node.completer:
                text = match.string[start:stop]

                # Unwrap text.
                unwrapped_text = node.unwrapper(text)

                # Create a document, for the completions API (text/cursor_position)
                document = Document(unwrapped_text, len(unwrapped_text))

                # Call completer
                for completion in node.completer.get_completions(document, complete_event):
                    new_text = unwrapped_text[:len(text) + completion.start_position] + completion.text

                    # Wrap again.
                    yield Completion(
                        text=node.wrapper(new_text),
                        start_position=start - len(match.string),
                        display=completion.display,
                        display_meta=completion.display_meta)

    def _remove_duplicates(self, items):
        """
        Remove duplicates, while keeping the order.
        (Sometimes we have duplicates, because the there several matches of the
        same grammar, each yielding similar completions.)
        """
        result = []
        for i in items:
            if i not in result:
                result.append(i)
        return result

