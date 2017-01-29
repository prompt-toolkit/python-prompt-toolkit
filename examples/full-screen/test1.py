#!/usr/bin/env python
"""
"""
from __future__ import unicode_literals

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.eventloop.defaults import create_event_loop
from prompt_toolkit.filters import HasFocus
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.registry import Registry, MergedRegistry, ConditionalRegistry
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import VSplit, HSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import BufferControl, FillControl, TokenListControl, UIControl, UIContent, UIControlKeyBindings, FillControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.lexers import PygmentsLexer
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import HighlightSearchProcessor, ReverseSearchProcessor
from prompt_toolkit.styles import style_from_pygments
from prompt_toolkit.token import Token

from pygments.lexers import HtmlLexer, CssLexer
from pygments.styles import get_style_by_name

class CustomControl(UIControl):
    def __init__(self, symbol):
        self.symbol = symbol
        self.text = ''

    def create_content(self, app, width, height):
        if app.focussed_control == self:
            token = Token.Focussed
        else:
            token = Token

        def create_line(num):
            if num == 0:
                return [(token, self.text)]
            return [(token, self.symbol * width)]
        return UIContent(create_line, line_count=height)

    def get_key_bindings(self, app):
        registry = Registry()

        @registry.add_binding('t')
        def _(event):
            self.text += 't'

        @registry.add_binding(Keys.Backspace)
        def _(event):
            self.text = self.text[:-1]

        return UIControlKeyBindings(ConditionalRegistry(registry, HasFocus(self)))

animal_completer = WordCompleter([
    'alligator', 'ant', 'ape', 'bat', 'bear', 'beaver', 'bee', 'bison',
    'butterfly', 'cat', 'chicken', 'crocodile', 'dinosaur', 'dog', 'dolphine',
    'dove', 'duck', 'eagle', 'elephant', 'fish', 'goat', 'gorilla', 'kangoroo',
    'leopard', 'lion', 'mouse', 'rabbit', 'rat', 'snake', 'spider', 'turkey',
    'turtle',
], ignore_case=True)


loop = create_event_loop()

c1 = CustomControl('x')
c2 = CustomControl('o')

search = Buffer(loop=loop)
b = Buffer(loop=loop, completer=animal_completer, complete_while_typing=False)

input_processor = None
#[
#    HighlightSearchProcessor(preview_search=True),
#]

c5 = BufferControl(buffer=search, input_processor=ReverseSearchProcessor())
c3 = BufferControl(buffer=b, input_processor=input_processor, lexer=PygmentsLexer(HtmlLexer), search_buffer_control=c5)
c4 = BufferControl(buffer=b, input_processor=input_processor, lexer=PygmentsLexer(CssLexer), search_buffer_control=c5)

layout = FloatContainer(HSplit([
    VSplit([
        Window(content=c1),
        Window(content=FillControl.from_character_and_token('*', Token.Star)),
        Window(content=c2),
        Window(content=c3),
        Window(content=c4),
    ]),
    Window(content=c5, height=D.exact(1)),
]), [
    Float(xcursor=True,
          ycursor=True,
          content=CompletionsMenu(max_height=16, scroll_offset=1))
])



registry = Registry()
handle = registry.add_binding

@handle(Keys.ControlC, eager=True)
@handle(Keys.ControlQ, eager=True)
def _(event):
    event.app.set_return_value(None)

@handle(Keys.ControlN, eager=True)
def _(event):
    " Change focus. "
    app = event.app
    controls = [c1, c2, c3]
    new_index = (controls.index(app.focussed_control) + 1) % len(controls)
    app.focussed_control = controls[new_index]


style = {
    Token.Focussed: 'bg:#0000ff #ffff00',
    Token.Star: 'bg:#ff0000',
    #Token: 'bg:#000000 #ffffff',
}


application = Application(
    loop=loop,
    layout=layout,
    key_bindings_registry=MergedRegistry([
        load_key_bindings(enable_search=True),  # Start with the `KeyBindingManager`.
        registry
    ]),
    style=style_from_pygments(get_style_by_name('default'), style),

    # Let's add mouse support!
    mouse_support=True,

    editing_mode = EditingMode.VI,

    # Using an alternate screen buffer means as much as: "run full screen".
    # It switches the terminal to an alternate screen.
    use_alternate_screen=True)


# 4. Run the application
#    -------------------

def run():
    try:
        application.run()
    finally:
        loop.close()

if __name__ == '__main__':
    run()
