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
from prompt_toolkit.layout.containers import VSplit, HSplit, Window, Align
from prompt_toolkit.layout.controls import BufferControl, FillControl, TokenListControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.layout.toolbars import TokenListToolbar
from prompt_toolkit.styles.from_dict import style_from_dict
from prompt_toolkit.token import Token
from prompt_toolkit.document import Document
from prompt_toolkit.utils import get_cwidth


loop = create_event_loop()


# <<<
class BORDER:
    " Box drawing characters. "
    HORIZONTAL = '\u2501'
    VERTICAL = '\u2503'
    TOP_LEFT = '\u250f'
    TOP_RIGHT = '\u2513'
    BOTTOM_LEFT = '\u2517'
    BOTTOM_RIGHT = '\u251b'
    LIGHT_VERTICAL = '\u2502'

def label(loop, text, token=None):
    if '\n' in text:
        width = None
    else:
        width = get_cwidth(text)

    buff = Buffer(loop=loop, document=Document(text))
    return Window(content=BufferControl(buff),
            align=Align.CENTER, token=token, width=D(preferred=width))

def create_button(text, action=None):
    def get_token(app):
        if app.layout.focussed_control == control:
            return Token.Button.Focussed
        else:
            return Token.Button

    def get_tokens(app):
        token = get_token(app)
        return [
            (token, '<'),
            (token.Text, '{}'.format(text)),
            (token, '>'),
        ]

    def get_char(app):
        return Char(' ', get_token(app))

    control = TokenListControl(
        get_tokens,
        get_default_char=get_char)

    return Window(control, align=Align.CENTER)


def create_text_field(loop, text=''):
    buff = Buffer(loop=loop)
    return Window(content=BufferControl(buffer=buff),
                  token=Token.TextField)

def create_frame(loop, body, title=' Title '):
#    assert isinstance(body, Container)

    return HSplit([
        VSplit([
            Window(width=D.exact(1), height=D.exact(1),
                   content=FillControl.from_character_and_token(
                       BORDER.TOP_LEFT, token=Token.Window.Border)),
            Window(FillControl.from_character_and_token(
                BORDER.HORIZONTAL, token=Token.Window.Border)),
            label(loop, title, token=Token.Label),
            Window(FillControl.from_character_and_token(
                BORDER.HORIZONTAL, token=Token.Window.Border)),
#            TokenListToolbar(
#                get_tokens=lambda app, ctrl: [(Token.Window.Title, ' %s ' % title)],
#                align_center=True,
#                default_char=Char(BORDER.HORIZONTAL, Token.Window.Border)),
            Window(width=D.exact(1), height=D.exact(1),
                   content=FillControl.from_character_and_token(
                       BORDER.TOP_RIGHT, token=Token.Window.Border)),
        ]),
        VSplit([
            Window(width=D.exact(1),
                   content=FillControl.from_character_and_token(
                       BORDER.VERTICAL, token=Token.Window.Border)),
            body,
            Window(width=D.exact(1),
                   content=FillControl.from_character_and_token(
                       BORDER.VERTICAL, token=Token.Window.Border)),
        ]),
        VSplit([
            Window(width=D.exact(1), height=D.exact(1),
                   content=FillControl.from_character_and_token(
                       BORDER.BOTTOM_LEFT, token=Token.Window.Border)),
            Window(height=D.exact(1),
                   content=FillControl.from_character_and_token(
                       BORDER.HORIZONTAL, token=Token.Window.Border)),
            Window(width=D.exact(1), height=D.exact(1),
                   content=FillControl.from_character_and_token(
                       BORDER.BOTTOM_RIGHT, token=Token.Window.Border)),
        ]),
    ])


# >>>


def create_pane():
    return Window(FillControl.from_character_and_token(' ', Token))

def vertical_line():
    return Window(FillControl.from_character_and_token(BORDER.VERTICAL, Token.Line), width=D.exact(1))

def horizontal_line():
    return Window(FillControl.from_character_and_token(BORDER.HORIZONTAL, Token.Line), height=D.exact(1))

yes_button = create_button('Yes')
no_button = create_button('No')
textfield = create_text_field(loop)

root_container = HSplit([
    VSplit([
        create_frame(loop, label(loop, 'hello world\ntest')),
        create_frame(loop, label(loop, 'right frame\ncontent')),
        create_frame(loop, label(loop, 'right frame\ncontent')),
    ]),
    VSplit([
        create_frame(loop, textfield),
        create_frame(loop, VSplit([
            create_frame(loop, label(loop, 'right frame\ncontent')),
            label(loop, 'right frame\ncontent'),
            vertical_line(),
            create_frame(loop, label(loop, 'right frame\ncontent')),
        ])),
    ]),
    create_pane(),
    VSplit([
        create_pane(),
        yes_button,
        create_pane(),
        no_button,
        create_pane(),
    ]),
    create_pane(),
])


bindings = KeyBindings()


#@bindings.add('y')
#@bindings.add('Y')
#def _(event):
#    event.app.set_return_value(True)
#
#@bindings.add('n')
#@bindings.add('N')
#def _(event):
#    event.app.set_return_value(False)


@bindings.add(Keys.Tab)
def _(event):
    widgets = [yes_button.content, no_button.content, textfield.content]
    index = widgets.index(event.app.layout.focussed_control)
    index = (index + 1) % len(widgets)
    event.app.layout.focussed_control = widgets[index]


@bindings.add(' ')
#@bindings.add(Keys.Enter)
def _(event):
    if event.app.layout.focussed_control == yes_button.content:
        event.app.set_return_value(True)
    elif event.app.layout.focussed_control == no_button.content:
        event.app.set_return_value(False)


style = style_from_dict({
    Token.Button: 'bg:#888888 #ffffff',
    Token.Button.Text: '',
    Token.Button.Focussed: 'bg:#880000 #ffffff',
    Token.Button.Focussed.Text: 'underline',
    Token.Label: 'reverse',
    Token.TextField: 'bg:#ffff00',
})


application = Application(
    loop=loop,
    layout=Layout(root_container, focussed_control=yes_button.content),
    key_bindings=MergedKeyBindings([
        load_key_bindings(),
        bindings,
    ]),
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
