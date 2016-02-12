"""
Processors are little transformation blocks that transform the token list from
a buffer before the BufferControl will render it to the screen.

They can insert tokens before or after, or highlight fragments by replacing the
token types.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from six import with_metaclass

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
    'BracketsMismatchProcessor',
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
    def apply_transformation(self, cli, document, lineno, tokens):
        """
        Apply transformation.  Returns a :class:`.Transformation` instance.
        """
        return Transformation(tokens)

    def has_focus(self, cli):
        """
        Processors can override the focus.
        (Used for the reverse-i-search prefix in DefaultPrompt.)
        """
        return False

    def invalidation_hash(self, cli, document):
        """
        Returns a hashable for invalidation. When this changes, the processor
        has to be applied again or the original input.
        """
        return None


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

    def apply_transformation(self, cli, document, lineno, tokens):
        search_text = self._get_search_text(cli)

        if search_text and not cli.is_returning:
            # For each search match, replace the Token.
            line_text = token_list_to_text(tokens)
            tokens = explode_tokens(tokens)

            # XXX: Take cursor position into account.
            flags = re.IGNORECASE if cli.is_ignoring_case else 0

            for match in re.finditer(re.escape(search_text), line_text, flags=flags):
                for i in range(match.start(), match.end()):
                    tokens[i] = (Token.SearchMatch, tokens[i][1])

            ##for index in document.find_all(search_text, ignore_case=ignore_case):
            ##    if index == document.cursor_position:
            ##        token = Token.SearchMatch.Current
            ##    else:
            ##        token = Token.SearchMatch

        ##return Transformation(document, tokens)
        return Transformation(tokens)

    def invalidation_hash(self, cli, document):
        search_text = self._get_search_text(cli)

        # When the search state changes, highlighting will be different.
        return (
            search_text,
            cli.is_returning,

            # XXX: include ignore_case in hash, if search_text is given.

            # When we search for text, and the cursor position changes. The
            # processor has to be applied every time again, because the current
            # match is highlighted in another color.
#            (search_text and document.cursor_position),
            search_text,
        )


class HighlightSelectionProcessor(Processor):
    """
    Processor that highlights the selection in the document.
    """
    def apply_transformation(self, cli, document, lineno, tokens):
        # In case of selection, highlight all matches.
        selection_at_line = document.selection_range_at_line(lineno)

        if selection_at_line:
            from_, to = selection_at_line
            tokens = explode_tokens(tokens)

            for i in range(from_, to + 1):
                if i < len(tokens):
                    tokens[i] = (Token.SelectedText, tokens[i][1])

        return Transformation(tokens)

    def invalidation_hash(self, cli, document):
        # When the search state changes, highlighting will be different.
        return (
            document.selection and (
                document.selection_range(),
                document.selection.type,
            )
        )


class PasswordProcessor(Processor):
    """
    Processor that turns masks the input. (For passwords.)

    :param char: (string) Character to be used. "*" by default.
    """
    def __init__(self, char='*'):
        self.char = char

    def apply_transformation(self, cli, document, lineno, tokens):
        # Returns (new_token_list, cursor_index_to_token_index_f)
        tokens = [(token, self.char * len(text)) for token, text in tokens]
        return Transformation(tokens)


class HighlightMatchingBracketProcessor(Processor):  # XXX: TODO
    """
    When the cursor is on or right after a bracket, it highlights the matching
    bracket.
    """
    _closing_braces = '])}>'

    def __init__(self, chars='[](){}<>'):
        self.chars = chars

    def apply_transformation(self, cli, document, lineno, tokens):
        def replace_token(pos):
            """ Replace token in list of tokens. """
            tokens[pos] = (Token.MatchingBracket, tokens[pos][1])

        def apply_for_document(document):
            """ Find and replace matching tokens. """
            if document.current_char in self.chars:
                pos = document.matching_bracket_position

                if pos:
                    replace_token(document.cursor_position)
                    replace_token(document.cursor_position + pos)
                    return True

        # Apply for character below cursor.
        applied = apply_for_document(document)

        # Otherwise, apply for character before cursor.
        if (not applied and document.cursor_position > 0 and
                document.char_before_cursor in self._closing_braces):
            apply_for_document(Document(document.text, document.cursor_position - 1))

#        return Transformation(document, tokens)
        return Transformation(tokens)

    def invalidation_hash(self, cli, document):
        on_brace = document.current_char in self.chars
        after_brace = document.char_before_cursor in self.chars

        if on_brace:
            return (True, document.cursor_position)
        elif after_brace and document.char_before_cursor in self._closing_braces:
            return (True, document.cursor_position - 1)
        else:
            # Don't include the cursor position in the hash if we are not *on*
            # a brace. We don't have to rerender the output, because it will be
            # the same anyway.
            return False


class BracketsMismatchProcessor(Processor):
    """
    Processor that replaces the token type of bracket mismatches by an Error.
    """
    error_token = Token.Error

    def apply_transformation(self, cli, document, lineno, tokens):  # TODO
        stack = []  # Pointers to the result array

        for index, (token, text) in enumerate(tokens):
            top = tokens[stack[-1]][1] if stack else ''

            if text in '({[]})':
                if text in '({[':
                    # Put open bracket on the stack
                    stack.append(index)

                elif (text == ')' and top == '(' or
                      text == '}' and top == '{' or
                      text == ']' and top == '['):
                    # Match found
                    stack.pop()
                else:
                    # No match for closing bracket.
                    tokens[index] = (self.error_token, text)

        # Highlight unclosed tags that are still on the stack.
        for index in stack:
            tokens[index] = (Token.Error, tokens[index][1])

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

    def apply_transformation(self, cli, document, lineno, tokens):
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

    def invalidation_hash(self, cli, document):
        # Redraw when the given tokens change.
        return tuple(self.get_tokens(cli))


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

    def apply_transformation(self, cli, document, lineno, tokens):
        tokens_after = self.get_tokens(cli)
        return Transformation(
#            document=document.insert_after(token_list_to_text(tokens_after)),
            tokens=tokens + self.get_tokens(cli))

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

    def invalidation_hash(self, cli, document):
        # Redraw when the given tokens change.
        return tuple(self.get_tokens(cli))


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

    def apply_transformation(self, cli, document, lineno, tokens):
        buffer = self._get_buffer(cli)

        if buffer.suggestion and buffer.document.is_cursor_at_the_end:
            suggestion = buffer.suggestion.text
        else:
            suggestion = ''

        return Transformation(
            #document=document.insert_after(suggestion),
            tokens=tokens + [(self.token, suggestion)])

    def invalidation_hash(self, cli, document):
        buffer = self._get_buffer(cli)

        # Redraw when the suggestion changes.
        if buffer.suggestion and document.is_cursor_at_the_end:
            return buffer.suggestion.text


class ShowLeadingWhiteSpaceProcessor(Processor):
    """
    Make leading whitespace visible.
    """
    def __init__(self, token=Token.LeadingWhiteSpace, char='\xb7'):
        self.token = token
        self.char = char

    def apply_transformation(self, cli, document, lineno, tokens):  # TODO
        # Walk through all te tokens.
        t = (self.token, self.char)
        is_start_of_line = True

        for i in range(len(tokens)):
            char = tokens[i][1]
            if is_start_of_line and char == ' ':
                tokens[i] = t
            elif char == '\n':
                is_start_of_line = True
            else:
                is_start_of_line = False

#        return Transformation(document, tokens)
        return Transformation(tokens)


class ShowTrailingWhiteSpaceProcessor(Processor):
    """
    Make trailing whitespace visible.
    """
    def __init__(self, token=Token.TrailingWhiteSpace, char='\xb7'):
        self.token = token
        self.char = char

    def apply_transformation(self, cli, document, lineno, tokens):  # TODO
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

    def apply_transformation(self, cli, document, lineno, tokens):
        # Run processor when enabled.
        if self.filter(cli):
            return self.processor.apply_transformation(cli, document, lineno, tokens)
        else:
            return Transformation(tokens)

    def has_focus(self, cli):
        if self.filter(cli):
            return self.processor.has_focus(cli)
        else:
            return False

    def invalidation_hash(self, cli, document):
        # When enabled, use the hash of the processor. Otherwise, just use
        # False.
        if self.filter(cli):
            return (True, self.processor.invalidation_hash(cli, document))
        else:
            return False

    def __repr__(self):
        return '%s(processor=%r, filter=%r)' % (
            self.__class__.__name__, self.processor, self.filter)
