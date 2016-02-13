"""
Processors are little transformation blocks that transform the token list from
a buffer before the BufferControl will render it to the screen.

They can insert tokens before or after, or highlight fragments by replacing the
token types.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from six import with_metaclass

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.document import Document
from prompt_toolkit.enums import SEARCH_BUFFER
from prompt_toolkit.filters import to_cli_filter
from prompt_toolkit.layout.utils import token_list_to_text
from prompt_toolkit.token import Token

from .utils import token_list_len, explode_tokens
from six.moves import range

import re

__all__ = (
    'Processor',
    'Transformation',

    'HighlightSearchProcessor',
    'HighlightSelectionProcessor',
    'PasswordProcessor',
    'HighlightMatchingBracketProcessor',
    'BeforeInput',
    'AfterInput',
    'AppendAutoSuggestion',
    'ConditionalProcessor',
    'ShowLeadingWhiteSpaceProcessor',
    'ShowTrailingWhiteSpaceProcessor',
)


class Processor(with_metaclass(ABCMeta, object)):
    """
    Manipulate the tokens for a given line in a
    :class:`~prompt_toolkit.layout.controls.BufferControl`.
    """
    @abstractmethod
    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        """
        Apply transformation.  Returns a :class:`.Transformation` instance.

        :param cli: :class:`.CommandLineInterface` instance.
        :param lineno: The number of the line to which we apply the processor.
        :param source_to_display: A function that returns the position in the
            `tokens` for any position in the source string. (This takes
            previous processors into account.)
        :param tokens: List of tokens that we can transform. (Received from the
            previous processor.)
        """
        return Transformation(tokens)

    def has_focus(self, cli):
        """
        Processors can override the focus.
        (Used for the reverse-i-search prefix in DefaultPrompt.)
        """
        return False


class Transformation(object):
    """
    Transformation result, as returned by :meth:`.Processor.apply_transformation`.

    Important: Always make sure that the length of `document.text` is equal to
               the length of all the text in `tokens`!

    :param tokens: The transformed tokens. To be displayed, or to pass to the
        next processor.
    :param source_to_display: Cursor position transformation from original string to
        transformed string.
    :param display_to_source: Cursor position transformed from source string to
        original string.
    """
    def __init__(self, tokens, source_to_display=None, display_to_source=None):
        self.tokens = tokens
        self.source_to_display = source_to_display or (lambda i: i)
        self.display_to_source = display_to_source or (lambda i: i)


class HighlightSearchProcessor(Processor):
    """
    Processor that highlights search matches in the document.
    Note that this doesn't support multiline search matches yet.

    :param preview_search: A Filter; when active it indicates that we take
        the search text in real time while the user is typing, instead of the
        last active search state.
    """
    def __init__(self, preview_search=False, search_buffer_name=SEARCH_BUFFER):
        self.preview_search = to_cli_filter(preview_search)
        self.search_buffer_name = search_buffer_name

    def _get_search_text(self, cli):
        """
        The text we are searching for.
        """
        # When the search buffer has focus, take that text.
        if self.preview_search(cli) and cli.buffers[self.search_buffer_name].text:
            return cli.buffers[self.search_buffer_name].text
        # Otherwise, take the text of the last active search.
        else:
            return cli.search_state.text

    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        search_text = self._get_search_text(cli)

        if search_text and not cli.is_returning:
            # For each search match, replace the Token.
            line_text = token_list_to_text(tokens)
            tokens = explode_tokens(tokens)

            flags = re.IGNORECASE if cli.is_ignoring_case else 0

            # Get cursor column.
            if document.cursor_position_row == lineno:
                cursor_column = source_to_display(document.cursor_position_col)
            else:
                cursor_column = None

            for match in re.finditer(re.escape(search_text), line_text, flags=flags):
                if cursor_column is not None:
                    on_cursor = match.start() <= cursor_column < match.end()
                else:
                    on_cursor = False

                for i in range(match.start(), match.end()):
                    if on_cursor:
                        tokens[i] = (Token.SearchMatch.Current, tokens[i][1])
                    else:
                        tokens[i] = (Token.SearchMatch, tokens[i][1])

        return Transformation(tokens)


class HighlightSelectionProcessor(Processor):
    """
    Processor that highlights the selection in the document.
    """
    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        # In case of selection, highlight all matches.
        selection_at_line = document.selection_range_at_line(lineno)

        if selection_at_line:
            from_, to = selection_at_line
            tokens = explode_tokens(tokens)

            for i in range(from_, to + 1):
                if i < len(tokens):
                    tokens[i] = (Token.SelectedText, tokens[i][1])

        return Transformation(tokens)


class PasswordProcessor(Processor):
    """
    Processor that turns masks the input. (For passwords.)

    :param char: (string) Character to be used. "*" by default.
    """
    def __init__(self, char='*'):
        self.char = char

    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        tokens = [(token, self.char * len(text)) for token, text in tokens]
        return Transformation(tokens)


class HighlightMatchingBracketProcessor(Processor):
    """
    When the cursor is on or right after a bracket, it highlights the matching
    bracket.

    :param max_cursor_distance: Only highlight matching brackets when the
        cursor is within this distance. (From inside a `Processor`, we can't
        know which lines will be visible on the screen. But we also don't want
        to scan the whole document for matching brackets on each key press, so
        we limit to this value.)
    """
    _closing_braces = '])}>'

    def __init__(self, chars='[](){}<>', max_cursor_distance=1000):
        self.chars = chars
        self.max_cursor_distance = max_cursor_distance

        self._positions_cache = SimpleCache(maxsize=8)

    def _get_positions_to_highlight(self, document):
        """
        Return a list of (row, col) tuples that need to be highlighted.
        """
        # Try for the character under the cursor.
        if document.current_char and document.current_char in self.chars:
            pos = document.find_matching_bracket_position(
                    start_pos=document.cursor_position - self.max_cursor_distance,
                    end_pos=document.cursor_position + self.max_cursor_distance)

        # Try for the character before the cursor.
        elif (document.char_before_cursor and document.char_before_cursor in
              self._closing_braces and document.char_before_cursor in self.chars):
            document = Document(document.text, document.cursor_position - 1)

            pos = document.find_matching_bracket_position(
                    start_pos=document.cursor_position - self.max_cursor_distance,
                    end_pos=document.cursor_position + self.max_cursor_distance)
        else:
            pos = None

        # Return a list of (row, col) tuples that need to be highlighted.
        if pos:
            pos += document.cursor_position  # pos is relative.
            row, col = document.translate_index_to_position(pos)
            return [(row, col), (document.cursor_position_row, document.cursor_position_col)]
        else:
            return []

    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        # Get the highlight positions.
        key = (cli.render_counter, document.text, document.cursor_position)
        positions = self._positions_cache.get(
            key, lambda: self._get_positions_to_highlight(document))

        # Apply if positions were foun at this line.
        if positions:
            for row, col in positions:
                if row == lineno:
                    tokens = explode_tokens(tokens)
                    tokens[col] = (Token.MatchingBracket, tokens[col][1])

        return Transformation(tokens)


class BeforeInput(Processor):
    """
    Insert tokens before the input.

    :param get_tokens: Callable that takes a
        :class:`~prompt_toolkit.interface.CommandLineInterface` and returns the
        list of tokens to be inserted.
    """
    def __init__(self, get_tokens):
        assert callable(get_tokens)
        self.get_tokens = get_tokens

    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        if lineno == 0:
            tokens_before = self.get_tokens(cli)
            tokens = tokens_before + tokens

            shift_position = token_list_len(tokens_before)
            source_to_display = lambda i: i + shift_position
            display_to_source = lambda i: i - shift_position
        else:
            source_to_display = None
            display_to_source = None

        return Transformation(tokens, source_to_display=source_to_display,
                              display_to_source=display_to_source)

    @classmethod
    def static(cls, text, token=Token):
        """
        Create a :class:`.BeforeInput` instance that always inserts the same
        text.
        """
        def get_static_tokens(cli):
            return [(token, text)]
        return cls(get_static_tokens)

    def __repr__(self):
        return '%s(get_tokens=%r)' % (
            self.__class__.__name__, self.get_tokens)


class AfterInput(Processor):
    """
    Insert tokens after the input.

    :param get_tokens: Callable that takes a
        :class:`~prompt_toolkit.interface.CommandLineInterface` and returns the
        list of tokens to be appended.
    """
    def __init__(self, get_tokens):
        assert callable(get_tokens)
        self.get_tokens = get_tokens

    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        # Insert tokens after the last line.
        if lineno == document.line_count - 1:
            return Transformation(tokens=tokens + self.get_tokens(cli))
        else:
            return Transformation(tokens=tokens)

    @classmethod
    def static(cls, text, token=Token):
        """
        Create a :class:`.AfterInput` instance that always inserts the same
        text.
        """
        def get_static_tokens(cli):
            return [(token, text)]
        return cls(get_static_tokens)

    def __repr__(self):
        return '%s(get_tokens=%r)' % (
            self.__class__.__name__, self.get_tokens)


class AppendAutoSuggestion(Processor):
    """
    Append the auto suggestion to the input.
    (The user can then press the right arrow the insert the suggestion.)

    :param buffer_name: The name of the buffer from where we should take the
        auto suggestion. If not given, we take the current buffer.
    """
    def __init__(self, buffer_name=None, token=Token.AutoSuggestion):
        self.buffer_name = buffer_name
        self.token = token

    def _get_buffer(self, cli):
        if self.buffer_name:
            return cli.buffers[self.buffer_name]
        else:
            return cli.current_buffer

    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        # Insert tokens after the last line.
        buffer = self._get_buffer(cli)

        if buffer.suggestion and buffer.document.is_cursor_at_the_end:
            suggestion = buffer.suggestion.text
        else:
            suggestion = ''

        return Transformation(tokens=tokens + [(self.token, suggestion)])


class ShowLeadingWhiteSpaceProcessor(Processor):
    """
    Make leading whitespace visible.
    """
    def __init__(self, token=Token.LeadingWhiteSpace, char='\xb7'):
        self.token = token
        self.char = char

    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        # Walk through all te tokens.
        t = (self.token, self.char)

        if tokens and token_list_to_text(tokens).startswith(' '):
            tokens = explode_tokens(tokens)

            for i in range(len(tokens)):
                if tokens[i][1] == ' ':
                    tokens[i] = t
                else:
                    break

        return Transformation(tokens)


class ShowTrailingWhiteSpaceProcessor(Processor):
    """
    Make trailing whitespace visible.
    """
    def __init__(self, token=Token.TrailingWhiteSpace, char='\xb7'):
        self.token = token
        self.char = char

    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        if tokens and tokens[-1][1].endswith(' '):
            t = (self.token, self.char)
            tokens = explode_tokens(tokens)

            # Walk backwards through all te tokens and replace whitespace.
            for i in range(len(tokens) - 1, -1, -1):
                char = tokens[i][1]
                if char == ' ':
                    tokens[i] = t
                else:
                    break

        return Transformation(tokens)


class ConditionalProcessor(Processor):
    """
    Processor that applies another processor, according to a certain condition.
    Example::

        # Create a function that returns whether or not the processor should
        # currently be applied.
        def highlight_enabled(cli):
            return true_or_false

        # Wrapt it in a `ConditionalProcessor` for usage in a `BufferControl`.
        BufferControl(input_processors=[
            ConditionalProcessor(HighlightSearchProcessor(),
                                 Condition(highlight_enabled))])

    :param processor: :class:`.Processor` instance.
    :param filter: :class:`~prompt_toolkit.filters.CLIFilter` instance.
    """
    def __init__(self, processor, filter):
        assert isinstance(processor, Processor)

        self.processor = processor
        self.filter = to_cli_filter(filter)

    def apply_transformation(self, cli, document, lineno, source_to_display, tokens):
        # Run processor when enabled.
        if self.filter(cli):
            return self.processor.apply_transformation(
                cli, document, lineno, source_to_display, tokens)
        else:
            return Transformation(tokens)

    def has_focus(self, cli):
        if self.filter(cli):
            return self.processor.has_focus(cli)
        else:
            return False

    def __repr__(self):
        return '%s(processor=%r, filter=%r)' % (
            self.__class__.__name__, self.processor, self.filter)
