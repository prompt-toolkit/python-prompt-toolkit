#!/usr/bin/env python
"""
"""
from __future__ import unicode_literals

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.eventloop.defaults import create_event_loop
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.registry import Registry, MergedRegistry
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, TokenListControl
from prompt_toolkit.layout.margins import ScrollbarMargin, NumberredMargin
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.lexers import PygmentsLexer
from prompt_toolkit.layout.processors import HighlightSearchProcessor
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.styles import PygmentsStyle
from prompt_toolkit.token import Token

from pygments.lexers import PythonLexer

# The main event loop. (Every application needs one.)
loop = create_event_loop()


# Create one text buffer for the main content.
default_buffer = Buffer(name=DEFAULT_BUFFER, loop=loop)

with open('./pager.py', 'rb') as f:
    default_buffer.text = f.read().decode('utf-8')


def get_statusbar_tokens(app):
    return [
        (Token.Status, './pager.py - '),
        (Token.Status.Position, '{}:{}'.format(
            default_buffer.document.cursor_position_row + 1,
            default_buffer.document.cursor_position_col + 1)),
        (Token.Status, ' - Press Ctrl-C to exit. ')
    ]


buffer_control = BufferControl(buffer=default_buffer, lexer=PygmentsLexer(PythonLexer))


layout = HSplit([
    # The top toolbar.
    Window(content=TokenListControl(
        get_statusbar_tokens, default_char=Char(token=Token.Status)),
        height=D.exact(1)),

    # The main content.
    Window(
        content=buffer_control,
        left_margins=[NumberredMargin()],
        right_margins=[ScrollbarMargin()]),

    #SearchToolbar(),
])


# Key bindings.
registry = Registry()

@registry.add_binding(Keys.ControlC)
@registry.add_binding('q')
def _(event):
    " Quit. "
    event.app.set_return_value(None)


style = PygmentsStyle.from_defaults({
    Token.Status: 'bg:#444444 #ffffff',
    Token.Status.Position: '#aaaa44',
})

# create application.
application = Application(
    loop=loop,
    layout=layout,
    key_bindings_registry=MergedRegistry([
        load_key_bindings(enable_search=True, enable_extra_page_navigation=True),
        registry,
    ]),
    mouse_support=True,
    style=style,
    focussed_control=buffer_control,

    # Using an alternate screen buffer means as much as: "run full screen".
    # It switches the terminal to an alternate screen.
    use_alternate_screen=True)


def run():
    try:
        application.run()

    finally:
        loop.close()

if __name__ == '__main__':
    run()
