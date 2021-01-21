#!/usr/bin/env python
"""
An example of select prompt.
"""

from prompt_toolkit.application import Application
from prompt_toolkit.filters import IsDone
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.containers import ConditionalContainer, HSplit


class SelectControl(FormattedTextControl):
    def __init__(self, options):
        self.options = options
        self.selected_index = 0
        super().__init__(key_bindings=self._create_key_bindings())

    @property
    def selected_option(self):
        return self.options[self.selected_index]

    def _create_key_bindings(self):
        kb = KeyBindings()
        count = len(self.options)

        @kb.add('down', eager=True)
        def move_cursor_down(event):
            self.selected_index = (self.selected_index + 1) % count

        @kb.add('up', eager=True)
        def move_cursor_up(event):
            self.selected_index = (self.selected_index - 1) % count

        @kb.add('enter', eager=True)
        def set_selected(event):
            value = self.selected_option
            event.app.exit(result=value)

        @kb.add('c-q', eager=True)
        @kb.add('c-c', eager=True)
        def _(event):
            raise KeyboardInterrupt()

        return kb

    def select_option_text(self, mark):
        text = []
        for idx, op in enumerate(self.options):
            if idx == self.selected_index:
                line = f'{mark} {op}\n'
            else:
                line = f'  {op}\n'
            text.append(('', line))  # style, string
        return text


def select_prompt(message, options, mark='>'):
    control = SelectControl(options)

    def get_formatted_text():
        return control.select_option_text(mark)

    layout = Layout(HSplit([
        Window(
            height=Dimension.exact(1),
            content=FormattedTextControl(
                lambda: message + '\n',
                show_cursor=False
            ),
        ),
        Window(
            height=Dimension.exact(len(control.options)),
            content=FormattedTextControl(get_formatted_text)
        ),
        ConditionalContainer(
            Window(control),
            filter=~IsDone()
        )
    ]))

    app = Application(
        layout=layout,
        key_bindings=control.key_bindings,
        full_screen=False
    )
    return app.run()


if __name__ == '__main__':
    result = select_prompt('select a option:', ['foo', 'bar'], mark='>')
    print(f'You selected {result}')
