#!/usr/bin/env python
"""
"""
from __future__ import unicode_literals

from functools import partial
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.eventloop.defaults import create_event_loop
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.key_bindings import KeyBindings, MergedKeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import VSplit, HSplit, Window, Align, to_window, FloatContainer, Float, Container
from prompt_toolkit.layout.controls import BufferControl, TokenListControl, UIControlKeyBindings
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.lexers import PygmentsLexer
from prompt_toolkit.styles.from_pygments import style_from_pygments
from prompt_toolkit.token import Token
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.eventloop.base import EventLoop
from pygments.lexers import HtmlLexer

loop = create_event_loop()


class BORDER:
    " Box drawing characters. "
    HORIZONTAL = '\u2501'
    VERTICAL = '\u2503'
    TOP_LEFT = '\u250f'
    TOP_RIGHT = '\u2513'
    BOTTOM_LEFT = '\u2517'
    BOTTOM_RIGHT = '\u251b'
    LIGHT_VERTICAL = '\u2502'


class TextArea(object):
    def __init__(self, loop, text=''):
        assert isinstance(loop, EventLoop)

        self.buffer = Buffer(loop=loop)

        self.window = Window(
            content=BufferControl(buffer=self.buffer, lexer=PygmentsLexer(HtmlLexer)),
            token=Token.TextArea,
            #align=Align.CENTER,
            wrap_lines=True)

    def __pt_container__(self):
        return self.window


class Label(object):
    def __init__(self, loop, text, token=None):
        assert isinstance(loop, EventLoop)

        if '\n' in text:
            width = D()
        else:
            width = D.exact(get_cwidth(text))

        buff = Buffer(loop=loop, document=Document(text, 0))
        self.window = Window(
            content=BufferControl(buff),
            # align=Align.CENTER,
            token=token, width=width)

    def __pt_container__(self):
        return self.window

class Fill(object):
    def __init__(self, token=Token, char=' ', width=None, height=None):
        self.window = Window(
            token=token,
            char=char,
            width=width,
            height=height)

    def __pt_container__(self):
        return self.window


class Frame(object):
    def __init__(self, loop, body, title=''):
        assert isinstance(loop, EventLoop)

        fill = partial(Fill, token=Token.Window.Border)

        self.container = HSplit([
            VSplit([
                fill(width=D.exact(1), height=D.exact(1), char=BORDER.TOP_LEFT),
                #Window(fill(BORDER.HORIZONTAL)),
                Label(loop, '{}'.format(title), token=Token.Frame.Label),
                fill(char=BORDER.HORIZONTAL),
                fill(width=D.exact(1), height=D.exact(1), char=BORDER.TOP_RIGHT),
            ]),
            VSplit([
                fill(width=D.exact(1), char=BORDER.VERTICAL),
                body,
                fill(width=D.exact(1), char=BORDER.VERTICAL),
            ]),
            VSplit([
                fill(width=D.exact(1), height=D.exact(1), char=BORDER.BOTTOM_LEFT),
                fill(char=BORDER.HORIZONTAL),
                fill(width=D.exact(1), height=D.exact(1), char=BORDER.BOTTOM_RIGHT),
            ]),
        ])

    def __pt_container__(self):
        return self.container


class MenuContainer(object):
    def __init__(self, body, menus=''):
        self.body = body

        self.container = FloatContainer(
            content=HSplit([
                # The titlebar.
                Window(height=D.exact(1),
                       content=TokenListControl(self._get_menu_tokens),
                        token=Token.MenuBar),

            #    # Horizontal separator.
            #    Window(height=D.exact(1),
            #           content=FillControl(char='-'),
            #           token=Token.Line),

                # The 'body', like defined above.
                body,
            ]),
            floats=[
                Float(top=1, left=1, content=self._file_menu(), transparant=False),
#                Float(content=dialog()),
            ]
        )

    def _get_menu_tokens(self, app):
        return [
            (Token.MenuBar, ' '),
            (Token.Menu, 'File'),
            (Token.MenuBar, ' Edit '),
            (Token.MenuBar, ' Info '),
        ]

    def _file_menu(self):
        def get_tokens(app):
            return [
                (Token.Menu, ' Open \n'),
                (Token.Menu, '------------\n'),
                (Token.Menu, ' Save \n'),
                (Token.Menu, ' Save as '),
            ]

        return Window(TokenListControl(get_tokens), token=Token.Menu)

    def __pt_container__(self):
        return self.container


class MenuItem(object):
    def __init__(self, text='', handler=None, submenu=None, shortcut=None):
        self.text = text
        self.handler = handler
        self.submenu = submenu
        self.shortcut = shortcut

class Menu(Container):
    def __init__(self, items):
        control = TokenListControl(self._get_tokens)




class Button(object):
    def __init__(self, text, action=None, width=12):
        assert callable(action)
        assert isinstance(width, int)

        self.text = text
        self.action = action
        self.width = width
        self.control = TokenListControl(
            self._get_tokens,
            get_key_bindings=self._get_key_bindings)

        self.window = Window(
            self.control,
            align=Align.CENTER,
            height=D.exact(1),
            width=D.exact(width),
            get_token=self._get_token)

    def _get_token(self, app):
        if app.layout.current_control == self.control:
            return Token.Button.Focussed
        else:
            return Token.Button

    def _get_tokens(self, app):
        token = Token.Button
        text = ('{:^%s}' % (self.width - 2)).format(self.text)

        if app.layout.current_control == self.control:
            return [
                (token.Arrow | token.Focussed, '<'),
                (token.Text | token.Focussed, text),
                (token.Arrow | token.Focussed, '>'),
            ]
        else:
            return [
                (token.Arrow, '<'),
                (token.Text, text),
                (token.Arrow, '>'),
            ]

    def _get_key_bindings(self, app):
        kb = KeyBindings()
        @kb.add(' ')
        @kb.add(Keys.Enter)
        def _(event):
            self.action(app)

        return UIControlKeyBindings(kb, modal=False)

    def __pt_container__(self):
        return self.window


class VerticalLine(object):
    def __init__(self):
        self.window = Fill(
            char=BORDER.VERTICAL,
            token=Token.Line,
            width=D.exact(1))

    def __pt_container__(self):
        return self.window


class HorizontalLine(object):
    def __init__(self):
        self.window = Fill(
            char=BORDER.HORIZONTAL,
            token=Token.Line,
            height=D.exact(1))

    def __pt_container__(self):
        return self.window

# >>>


def create_pane():
    return Window()


def accept_yes(app):
    app.set_return_value(True)

def accept_no(app):
    app.set_return_value(False)


# Make partials that pass the loop everywhere.
Frame_ = partial(Frame, loop=loop)
Button_ = partial(Button, loop=loop)
Label_ = partial(Label, loop=loop)
TextField_ = partial(TextArea, loop=loop)


yes_button = Button('Yes', action=accept_yes)
no_button = Button('No', action=accept_no)
textfield = TextField_()
textfield2 = TextField_()

root_container = HSplit([
    VSplit([
#        Frame_(title='Test', body=Label('hello world\ntest')),
        Frame_(body=Label_(text='right frame\ncontent')),
        Frame_(title='Hello', body=Label_(text='right frame\ncontent')),
    ]),
    VSplit([
        Frame_(body=textfield),
        Frame_(body=VSplit([
            Frame_(body=Label_(text='right frame\ncontent')),
            Label_(text='right frame\ncontent'),
            VerticalLine(),
            Frame_(body=Label_(text='right frame\ncontent')),
        ])),
        Frame_(body=textfield2),
    ]),
    create_pane(),
    VSplit([
        create_pane(),
        yes_button,
        no_button,
        create_pane(),
    ]),
    create_pane(),
])

root_container = MenuContainer(root_container)

# Global key bindings.

bindings = KeyBindings()

widgets = [to_window(w) for w in
    (yes_button, no_button, textfield, textfield2)
]

@bindings.add(Keys.Tab)
def _(event):
    index = widgets.index(event.app.layout.current_window)
    index = (index + 1) % len(widgets)
    event.app.layout.focus(widgets[index])

@bindings.add(Keys.BackTab)
def _(event):
    index = widgets.index(event.app.layout.current_window)
    index = (index - 1) % len(widgets)
    event.app.layout.focus(widgets[index])


style = style_from_pygments(style_dict={
    Token.Button.Text: '#888888',
    Token.Button.Focussed: 'reverse',
    Token.Button.Arrow: 'bold',
    Token.Button.Focussed: 'bg:#880000 #ffffff',
    Token.TextArea: 'bg:#ffffaa',
    Token.Focussed: 'bg:#33ff00',
    Token.Label: '#888888 reverse',
    Token.Window.Border: '#888888',

    Token.MenuBar: 'bg:#0000ff #ffff00',
    Token.Menu: 'bg:#008888 #ffffff',
    Token.DialogTitle: 'bg:#444444 #ffffff',
    Token.DialogBody: 'bg:#888888',
})


application = Application(
    loop=loop,
    layout=Layout(root_container, focussed_window=yes_button.__pt_container__()),
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
