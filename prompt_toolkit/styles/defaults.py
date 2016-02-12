"""
The default styling.
"""
from __future__ import unicode_literals

from prompt_toolkit.token import Token

__all__ = (
    'DEFAULT_STYLE_EXTENSIONS',
    'default_style_extensions',
)


#: Styling of prompt-toolkit specific tokens, that are not know by the default
#: Pygments style.
DEFAULT_STYLE_EXTENSIONS = {
    # Highlighting of search matches in document.
    Token.SearchMatch:                            '#000000 bg:#888888',
    Token.SearchMatch.Current:                    '#ffffff bg:#aa8888 underline',

    # Highlighting of select text in document.
    Token.SelectedText:                           '#ffffff bg:#666666',

    # Highlighting of matching brackets.
    Token.MatchingBracket:                        'bg:#aaaaff #000000',

    # Line numbers.
    Token.LineNumber:                             '#888888',
    Token.LineNumber.Current:                     'bold',
    Token.Tilde:                                  '#8888ff',

    # Default prompt.
    Token.Prompt:                                 'bold',
    Token.Prompt.Arg:                             'noinherit',
    Token.Prompt.Search:                          'noinherit',
    Token.Prompt.Search.Text:                     'bold',

    # Search toolbar.
    Token.Toolbar.Search:                         'bold',
    Token.Toolbar.Search.Text:                    'nobold',

    # System toolbar
    Token.Toolbar.System:                         'bold',

    # "arg" toolbar.
    Token.Toolbar.Arg:                            'bold',
    Token.Toolbar.Arg.Text:                       'nobold',

    # Validation toolbar.
    Token.Toolbar.Validation:                     'bg:#550000 #ffffff',
    Token.WindowTooSmall:                         'bg:#550000 #ffffff',

    # Completions toolbar.
    Token.Toolbar.Completions:                    'bg:#bbbbbb #000000',
    Token.Toolbar.Completions.Arrow:              'bg:#bbbbbb #000000 bold',
    Token.Toolbar.Completions.Completion:         'bg:#bbbbbb #000000',
    Token.Toolbar.Completions.Completion.Current: 'bg:#444444 #ffffff',

    # Completions menu.
    Token.Menu.Completions:                       'bg:#bbbbbb #000000',
    Token.Menu.Completions.Completion:            '',
    Token.Menu.Completions.Completion.Current:    'bg:#888888 #ffffff',
    Token.Menu.Completions.Meta:                  'bg:#999999 #000000',
    Token.Menu.Completions.Meta.Current:          'bg:#aaaaaa #000000',
    Token.Menu.Completions.MultiColumnMeta:       'bg:#aaaaaa #000000',

    # Scrollbars.
    Token.Scrollbar:                              'bg:#888888',
    Token.Scrollbar.Button:                       'bg:#444444',
    Token.Scrollbar.Arrow:                        'bg:#222222 #888888 bold',

    # Auto suggestion text.
    Token.AutoSuggestion:                         '#666666',

    # When Control-C has been pressed. Grayed.
    Token.Aborted:                                '#888888',
}

default_style_extensions = DEFAULT_STYLE_EXTENSIONS  # Old name.
