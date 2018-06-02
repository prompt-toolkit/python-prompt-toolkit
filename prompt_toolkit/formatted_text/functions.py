"""
Shortcuts for turning pieces of text into color.
This can be used for printing text with a certain formatting, but also for
transforming formatted text.

Each of the functions here can take any kind of plain text or formatted text as input.
"""
from .base import to_formatted_text, FormattedText
from prompt_toolkit.styles.named_colors import NAMED_COLORS

__all__ = [
    'ansired',
    'ansiblue',
    'ansiyellow',


    'ansibrightblack',
    'ansibrightred',
    'ansibrightgreen',
    'ansibrightyellow',
    'ansibrightblue',
    'ansibrightmagenta',
    'ansibrightcyan',
    'ansiwhite',

    'underline',
    'bold',
    'italic',
] + [name.lower() for name in NAMED_COLORS]


def _create_format_func(name, formatting):
    def func(*text):
        return _apply_style(text, formatting)
    func.__name__ = name
    func.__doc__ = """
    Apply the following formatting: {}.

    :param text: Any kind of plain text or formatted text. (Multiple pieces can
        be given.)
    """.format(formatting)
    return func


def _apply_style(text, formatting):
    " Helper for creating the format functions below. "
    fragments = []

    for part in text:
        part = to_formatted_text(part)
        fragments.extend([(style + ' ' + formatting, v) for style, v in part])

    return FormattedText(fragments)


# Special formatting.
underline = _create_format_func('underline', 'underline')
bold = _create_format_func('bold', 'bold')
italic = _create_format_func('italic', 'italic')


# ANSI colors (written manually on purpose, that works better for Jedi auto completion).
ansiblack = _create_format_func('ansiblack', 'fg:ansiblack')
ansired = _create_format_func('ansired', 'fg:ansired')
ansigreen = _create_format_func('ansigreen', 'fg:ansigreen')
ansiyellow = _create_format_func('ansiyellow', 'fg:ansiyellow')
ansiblue = _create_format_func('ansiblue', 'fg:ansiblue')
ansimagenta = _create_format_func('ansimagenta', 'fg:ansimagenta')
ansicyan = _create_format_func('ansicyan', 'fg:ansicyan')
ansigray = _create_format_func('ansigray', 'fg:ansigray')

ansibrightblack = _create_format_func('ansibrightblack', 'fg:ansibrightblack')
ansibrightred = _create_format_func('ansibrightred', 'fg:ansibrightred')
ansibrightgreen = _create_format_func('ansibrightgreen', 'fg:ansibrightgreen')
ansibrightyellow = _create_format_func('ansibrightyellow', 'fg:ansibrightyellow')
ansibrightblue = _create_format_func('ansibrightblue', 'fg:ansibrightblue')
ansibrightmagenta = _create_format_func('ansibrightmagenta', 'fg:ansibrightmagenta')
ansibrightcyan = _create_format_func('ansibrightcyan', 'fg:ansibrightcyan')
ansiwhite = _create_format_func('ansiwhite', 'fg:ansiwhite')


# 256 named colors.
for name in NAMED_COLORS:
    name = name.lower()
    globals()[name] = _create_format_func(name, 'fg:' + name)
