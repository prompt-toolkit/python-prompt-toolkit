#!/usr/bin/env python
"""
"""
from __future__ import unicode_literals

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.eventloop.defaults import create_event_loop
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.key_bindings import KeyBindings, MergedKeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import VSplit, HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FillControl, TokenListControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.styles.from_dict import style_from_dict
from prompt_toolkit.token import Token


loop = create_event_loop()

def create_button(text, action=None):
    def get_tokens(app):
        return [
            (Token.Button, '\n {} \n'.format(text))
        ]

    return TokenListControl(
        get_tokens,
        default_char=Char(' ', Token.Button),
        align_center=True)

def create_pane():
    return Window(FillControl.from_character_and_token(' ', Token))


yes_button = create_button('Yes')
no_button = create_button('No')
no_button = create_button('No')

root_container = HSplit([
    create_pane(),
    VSplit([
        create_pane(),
        Window(yes_button, height=D.exact(3)),
        create_pane(),
        Window(no_button, height=D.exact(3)),
        create_pane(),
    ]),
    create_pane(),
])


bindings = KeyBindings()


@bindings.add('y')
@bindings.add('Y')
def _(event):
    event.app.set_return_value(True)

@bindings.add('n')
@bindings.add('N')
def _(event):
    event.app.set_return_value(False)

@bindings.add(Keys.Tab)
def _(event):
    if event.app.layout.focussed_control == yes_button:
        event.app.layout.focussed_control = no_button
    else:
        event.app.layout.focussed_control = yes_button


style = style_from_dict({
    Token.Button: 'bg:#222222 #ffffff',
})


application = Application(
    loop=loop,
    layout=Layout(root_container, focussed_control=yes_button),
    key_bindings=bindings,
    style=style,

    # Let's add mouse support!
    mouse_support=True,

    # Using an alternate screen buffer means as much as: "run full screen".
    # It switches the terminal to an alternate screen.
    use_alternate_screen=True)



def run():
    result = application.run()
    print('You said: %r' % result)


if __name__ == '__main__':
    run()
