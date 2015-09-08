"""
User interface Controls for the layout.
"""
from __future__ import unicode_literals
from pygments.token import Token

from six import with_metaclass
from abc import ABCMeta, abstractmethod

from prompt_toolkit.filters import to_cli_filter
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.search_state import SearchState
from prompt_toolkit.enums import DEFAULT_BUFFER

from .lexers import Lexer, SimpleLexer
from .margins import Margin, NoMargin
from .processors import Processor
from .screen import Screen, Char, Point
from .utils import token_list_width

__all__ = (
    'TokenListControl',
    'FillControl',
    'BufferControl',
)


class UIControl(with_metaclass(ABCMeta, object)):
    """
    Base class for all user interface controls.
    """
    def reset(self):
        # Default reset. (Doesn't have to be implemented.)
        pass

    def preferred_width(self, cli, max_available_width):
        return None

    def preferred_height(self, cli, width):
        return None

    def has_focus(self, cli):
        return False

    @abstractmethod
    def create_screen(self, cli, width, height):
        """
        Write the content at this position to the screen.
        """
        pass


class _SimpleLRUCache(object):
    """
    Very simple LRU cache.

    :param maxsize: Maximum size of the cache. (Don't make it too big.)
    """
    def __init__(self, maxsize=8):
        self.maxsize = maxsize
        self._cache = []  # List of (key, value).

    def get(self, key, getter_func):
        """
        Get object from the cache.
        If not found, call `getter_func` to resolve it, and put that on the top
        of the cache instead.
        """
        # Look in cache first.
        for k, v in self._cache:
            if k == key:
                return v

        # Not found? Get it.
        value = getter_func()
        self._cache.append((key, value))

        if len(self._cache) > self.maxsize:
            self._cache = self._cache[-self.maxsize:]

        return value


class TokenListControl(UIControl):
    """
    Control that displays a list of (Token, text) tuples.

    :param get_tokens: Callable that takes a `CommandLineInterface` instance
        and returns the list of (Token, text) tuples to be displayed right now.
    :param default_char: default `Char` (character and Token) to use for the
        background when there is more space available than `get_tokens` returns.
    :param has_focus: `bool` or `CLIFilter`, when this evaluates to `True`,
        this UI control will take the focus. The cursor will be shown in the
        upper left corner of this control, unless `get_token` returns a
        `Token.SetCursorPosition` token somewhere in the token list, then the
        cursor will be shown there.
    """
    def __init__(self, get_tokens, default_char=None, align_right=False, align_center=False,
                 has_focus=False):
        assert default_char is None or isinstance(default_char, Char)

        self.get_tokens = get_tokens
        self.default_char = default_char or Char(' ', Token)
        self.align_right = to_cli_filter(align_right)
        self.align_center = to_cli_filter(align_center)
        self._has_focus_filter = to_cli_filter(has_focus)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.get_tokens)

    def has_focus(self, cli):
        return self._has_focus_filter(cli)

    def preferred_width(self, cli, max_available_width):
        """
        Return the preferred width for this control.
        That is the width of the longest line.
        """
        text = ''.join(t[1] for t in self.get_tokens(cli))
        line_lengths = [get_cwidth(l) for l in text.split('\n')]
        return max(line_lengths)

    def preferred_height(self, cli, width):
        screen = self.create_screen(cli, width, None)
        return screen.current_height

    def create_screen(self, cli, width, height):
        screen = Screen(width, self.default_char)

        # Get tokens
        tokens = self.get_tokens(cli)

        # Only call write_data when we actually have tokens.
        # (Otherwise the screen height will go up from 0 to 1 while we don't
        # want that. -- An empty control should not take up any space.)
        if tokens:
            # Align right/center.
            right = self.align_right(cli)
            center = self.align_center(cli)

            if right or center:
                used_width = token_list_width(tokens)
                padding = width - used_width
                if center:
                    padding = int(padding / 2)
                tokens = [(self.default_char.token, self.default_char.char * padding)] + tokens

            screen.write_data(tokens, width)
        return screen

    @classmethod
    def static(cls, tokens):
        def get_static_tokens(cli):
            return tokens
        return cls(get_static_tokens)


class FillControl(UIControl):
    """
    Fill whole control with characters with this token.
    (Also helpful for debugging.)
    """
    def __init__(self, character=' ', token=Token):
        self.token = token
        self.character = character

    def __repr__(self):
        return '%s(character=%r, token=%r)' % (
            self.__class__.__name__, self.character, self.token)

    def reset(self):
        pass

    def has_focus(self, cli):
        return False

    def create_screen(self, cli, width, height):
        char = Char(self.character, self.token)
        screen = Screen(width, char)
        screen.current_height = height
        return screen


class BufferControl(UIControl):
    """
    Control for visualising the content of a `Buffer`.

    :param input_processors: list of `InputProcessor.
    :param lexer: Pygments lexer class.
    :param preview_search: `bool` or `CLIFilter`: Show search while typing.
    :param buffer_name: String representing the name of the buffer to display.
    :param margin: `Margin` instance. for instance: `NumberredMargin` in order
        to show line numbers.
    :param default_char: `Char` instance to use to fill the background. This is
        transparent by default.
    """
    def __init__(self,
                 input_processors=None,
                 lexer=None,
                 preview_search=False,
                 buffer_name=DEFAULT_BUFFER,
                 menu_position=None,
                 margin=None,
                 default_char=None):
        assert input_processors is None or all(isinstance(i, Processor) for i in input_processors)
        assert menu_position is None or callable(menu_position)
        assert margin is None or isinstance(margin, Margin)
        assert lexer is None or isinstance(lexer, Lexer)

        self.preview_search = to_cli_filter(preview_search)

        self.input_processors = input_processors or []
        self.buffer_name = buffer_name
        self.menu_position = menu_position
        self.margin = margin or NoMargin()
        self.lexer = lexer or SimpleLexer()
        self.default_char = default_char or Char(token=Token.Transparent)

        #: LRU cache for the lexer.
        #: Often, due to cursor movement, undo/redo and window resizing
        #: operations, it happens that a short time, the same document has to be
        #: lexed. This is a faily easy way to cache such an expensive operation.
        self._token_lru_cache = _SimpleLRUCache(maxsize=8)

        #: Keep a similar cache for rendered screens. (when we scroll up/down
        #: through the screen, or when we change another buffer, we don't want
        #: to recreate the same screen again.)
        self._screen_lru_cache = _SimpleLRUCache(maxsize=8)

    def _buffer(self, cli):
        """
        The buffer object that contains the 'main' content.
        """
        return cli.buffers[self.buffer_name]

    def has_focus(self, cli):
        # This control gets the focussed if the actual `Buffer` instance has the
        # focus or when any of the `InputProcessor` classes tells us that it
        # wants the focus. (E.g. in case of a reverse-search, where the actual
        # search buffer may not be displayed, but the "reverse-i-search" text
        # should get the focus.)
        return cli.focus_stack.current == self.buffer_name or \
            any(i.has_focus(cli) for i in self.input_processors)

    def preferred_width(self, cli, max_available_width):
        # Return the length of the longest line.
        return max(map(len, self._buffer(cli).document.lines))

    def preferred_height(self, cli, width):
        # Draw content on a screen using this width. Measure the height of the
        # result.
        screen = self.create_screen(cli, width, None)
        return screen.current_height

    def _get_input_tokens(self, cli, buffer):
        """
        Tokenize input text for highlighting.
        Return (tokens, cursor_transform_functions) tuple.

        :param buffer: The Buffer instance.
        :param document: The document to be shown. This can be `buffer.document`
                         but could as well be a different one, in case we are
                         searching through the history.
        """
        def get():
            # Call lexer.
            tokens = list(self.lexer.get_tokens(cli, buffer.document.text))

            # 'Explode' tokens in characters.
            # (Some input processors -- like search/selection highlighter --
            # rely on that each item in the tokens array only contains one
            # character.)
            tokens = [(token, c) for token, text in tokens for c in text]

            # Run all processors over the input.
            # (They can transform both the tokens and the cursor position.)
            cursor_transform_functions = []

            for p in self.input_processors:
                tokens, f = p.run(cli, buffer, tokens)
                cursor_transform_functions.append(f)

            return tokens, cursor_transform_functions

        key = (
            buffer.document.text,

            # Include invalidation_hashes from all processors.
            tuple(p.invalidation_hash(cli, buffer) for p in self.input_processors),
        )

        return self._token_lru_cache.get(key, get)

    def create_screen(self, cli, width, height):
        buffer = self._buffer(cli)

        # Get the document to be shown. If we are currently searching (the
        # search buffer has focus, and the preview_search filter is enabled),
        # then use the search document, which has possibly a different
        # text/cursor position.)
        def preview_now():
            """ True when we should preview a search. """
            return bool(self.preview_search(cli) and
                    cli.is_searching and cli.current_buffer.text)

        if preview_now():
            document = buffer.document_for_search(SearchState(
                text=cli.current_buffer.text,
                direction=cli.search_state.direction,
                ignore_case=cli.search_state.ignore_case))
        else:
            document = buffer.document

        def _create_screen():
            screen = Screen(width, self.default_char)

            # Get tokens
            # Note: we add the space character at the end, because that's where
            #       the cursor can also be.
            input_tokens, cursor_transform_functions = self._get_input_tokens(cli, buffer)
            input_tokens += [(Token, ' ')]

            indexes_to_pos = screen.write_data(
                input_tokens,
                screen.width,
                margin=self.margin.create_handler(cli, buffer.document))

            def cursor_position_to_xy(cursor_position):
                # First get the real token position by applying all
                # transformations from the input processors.
                for f in cursor_transform_functions:
                    cursor_position = f(cursor_position)

                # Then look up into the table.
                try:
                    return indexes_to_pos[cursor_position]
                except KeyError:
                    # This can fail with KeyError, but only if one of the
                    # processors is returning invalid key locations.
                    raise
                    # return 0, 0

            return screen, cursor_position_to_xy

        # Build a key for the caching. If any of these parameters changes, we
        # have to recreate a new screen.
        key = (
            # When the text changes, we obviously have to recreate a new screen.
            document.text,

            # When the width changes, line wrapping will be different.
            # TODO: allow to disable line wrapping. + in that case, remove 'width'
            width,

            # When line numbers are enabled/disabled. (Or whatever parameters
            # the margin has.)
            self.margin.invalidation_hash(cli, document),

            # Include invalidation_hashes from all processors.
            tuple(p.invalidation_hash(cli, buffer) for p in self.input_processors),
        )

        # Get from cache, or create if this doesn't exist yet.
        screen, cursor_position_to_xy = self._screen_lru_cache.get(key, _create_screen)

        x, y = cursor_position_to_xy(document.cursor_position)
        screen.cursor_position = Point(y=y, x=x)

        # If there is an auto completion going on, use that start point for a
        # pop-up menu position. (But only when this buffer has the focus --
        # there is only one place for a menu, determined by the focussed buffer.)
        if cli.current_buffer_name == self.buffer_name:
            menu_position = self.menu_position(cli) if self.menu_position else None
            if menu_position is not None:
                assert isinstance(menu_position, int)
                x, y = cursor_position_to_xy(menu_position)
                screen.menu_position = Point(y=y, x=x)
            elif buffer.complete_state:
                # Position for completion menu.
                # Note: We use 'min', because the original cursor position could be
                #       behind the input string when the actual completion is for
                #       some reason shorter than the text we had before. (A completion
                #       can change and shorten the input.)
                x, y = cursor_position_to_xy(
                    min(buffer.cursor_position,
                        buffer.complete_state.original_document.cursor_position))
                screen.menu_position = Point(y=y, x=x)
            else:
                screen.menu_position = None

        return screen
