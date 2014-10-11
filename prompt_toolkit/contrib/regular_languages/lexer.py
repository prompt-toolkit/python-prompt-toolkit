"""
`GrammarLexer` is compatible with Pygments lexers and can be used to highlight
the input using a regular grammar with token annotations.
"""
from __future__ import unicode_literals
from pygments.token import Token

from .compiler import _CompiledGrammar

__all__ = (
    'GrammarLexer',
)


class GrammarLexer(object):
    """
    Lexer which uses the tokens as defined in the variables of a grammar.

    (It does not actual lexing of the string, but it exposes an API, compatible
    with the Pygments lexer class.)
    """
    def __init__(self, compiled_grammar):
        assert isinstance(compiled_grammar, _CompiledGrammar)
        self.compiled_grammar = compiled_grammar

    def __call__(self, stripnl=False, stripall=False, ensurenl=False):
        """
        For compatibility with Pygments lexers.
        (Signature of Pygments Lexer.__init__)
        """
        return self

    def get_tokens(self, text):
        m = self.compiled_grammar.match_prefix(text)

        if m:
            characters = [[Token, c] for c in text]

            for v in m.variables():
                # If we have a Pygmenst lexer for this part of the input.
                # Tokenize recursively and apply tokens.
                if v.node.lexer:
                    lexer_tokens = v.node.lexer.get_tokens(text[v.start:v.stop])
                    i = v.start
                    for t, s in lexer_tokens:
                        for c in s:
                            characters[i][0] = t
                            i += 1

                elif v.node.token:
                    for i in range(v.start, v.stop):
                        if characters[i][0] == Token:
                            characters[i][0] = v.node.token
            return characters
        else:
            return [(Token, text)]
