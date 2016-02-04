"""
Lexer interface and implementation.
Used for syntax highlighting.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from six import with_metaclass

from prompt_toolkit.token import Token
from prompt_toolkit.filters import to_cli_filter
from .utils import split_lines

__all__ = (
    'Lexer',
    'SimpleLexer',
    'PygmentsLexer',
)


class Lexer(with_metaclass(ABCMeta, object)):
    """
    Base class for all lexers.
    """
    @abstractmethod
    def lex_document(self, cli, document):
        """
        Takes a :class:`~prompt_toolkit.document.Document` and returns a
        callable that takes a line number and returns the tokens for that line.
        """
        lines = document.lines

        def get_line(lineno):
            " Return the tokens for the given line. "
            return [(Token, lines[lineno])]
        return get_line


class SimpleLexer(Lexer):
    """
    Lexer that returns everything as just one token.
    """
    def __init__(self, default_token=Token):
        self.default_token = default_token

    def lex_document(self, cli, document):
        lines = document.lines

        def get_line(lineno):
            try:
                return [(self.default_token, lines[lineno])]
            except IndexError:
                return []
        return get_line


class PygmentsLexer(Lexer):
    """
    Lexer that calls a pygments lexer.
    """
    def __init__(self, pygments_lexer_cls, sync_from_start=False):
        self.pygments_lexer_cls = pygments_lexer_cls
        self.sync_from_start = to_cli_filter(sync_from_start)

        # Instantiate the Pygments lexer.
        self.pygments_lexer = pygments_lexer_cls(
            stripnl=False,
            stripall=False,
            ensurenl=False)

    @classmethod
    def from_filename(cls, filename, sync_from_start=False):
        """
        Create a `Lexer` from a filename.
        """
        from pygments.util import ClassNotFound
        from pygments.lexers import get_lexer_for_filename

        try:
            pygments_lexer = get_lexer_for_filename(filename)
        except ClassNotFound:
            return SimpleLexer()
        else:
            return cls(pygments_lexer.__class__, sync_from_start=sync_from_start)

    def lex_document(self, cli, document):
        from_start = self.sync_from_start(cli)

        # Cache of already lexed lines.
        cache = {}

        # Pygments generators that are currently lexing.
        line_generators = {}  # Map lexer generator to the line number.

        def create_line_generator(start_lineno):
            """
            Create a generator that yields the lexed lines.
            Each iteration it yields a (line_number, [(token, text), ...]) tuple.
            """
            text = '\n'.join(document.lines[start_lineno:])
            return enumerate(split_lines(self.pygments_lexer.get_tokens(text)), start_lineno)

        def get_line(i):
            " Return the tokens for a given line number. "
            try:
                return cache[i]
            except KeyError:
                # Find closest line generator.
                if from_start:
                    if line_generators:
                        return line_generators.keys()[0]
                    else:
                        generator = create_line_generator(0)
                        line_generators[generator] = 0
                else:
                    for generator, lineno in line_generators.items():
                        if lineno < i and i - lineno < 100:
                            break
                    else:
                        # Go at least 200 lines back. (Make scrolling upwards
                        # more efficient.)
                        startpos = max(0, i - 200)

                        generator = create_line_generator(startpos)
                        line_generators[generator] = startpos

                # Exhaust the generator, until we find the requested line.
                for num, line in generator:
                    cache[num] = line
                    if num == i:
                        line_generators[generator] = i

                        # Remove the next item from the cache.
                        # (It could happen that it's already there, because of
                        # another generator that started filling these lines,
                        # but we want to synchronise these lines with the
                        # current lexer's state.)
                        if num + 1 in cache:
                            del cache[num + 1]

                        return cache[num]
            return []

        return get_line
