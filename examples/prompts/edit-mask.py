#!/usr/bin/env python
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.completion import FuzzyWordCompleter
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Float
from prompt_toolkit.layout.containers import FloatContainer
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.menus import CompletionsMenuControl
from prompt_toolkit.widgets import TextArea


class EditMask:
    def __init__(self, animals=None, colors=None, cities=None, names=None):
        self.animal_completer = FuzzyWordCompleter(animals)
        self.color_completer = FuzzyWordCompleter(colors)
        self.city_completer = FuzzyWordCompleter(cities)
        self.name_completer = FuzzyWordCompleter(names)

        self.finish_event = ''

        kb = KeyBindings()

        @Condition
        def is_not_autocompleting():
            "Check if the completion menu is visible"
            for vw in get_app().layout.visible_windows:
                if type(vw.content) is CompletionsMenuControl:
                    return False
            return True

        @kb.add("down", filter=is_not_autocompleting)
        def _(event):
            "Move to next item."
            get_app().layout.focus_next()

        @kb.add("up", filter=is_not_autocompleting)
        def _(event):
            "Move to previous item."
            get_app().layout.focus_previous()

        @kb.add("c-c")
        def _(event):
            "Quit application without saving."
            self.finish_event = 'quit'
            event.app.exit()

        @kb.add("c-s")
        def _(event):
            "Save and quit application."
            self.finish_event = 'save'
            event.app.exit()

        self.text_area = {
            'Animal': self.factory_area(
                'Animal',
                prefix_min_width=15,
                completer=self.animal_completer
            ),
            'Color': self.factory_area(
                'Color',
                prefix_min_width=15,
                completer=self.color_completer
            ),
            'City': self.factory_area(
                'City',
                prefix_min_width=15,
                completer=self.city_completer
            ),
            'Name': self.factory_area(
                'Name',
                prefix_min_width=15,
                completer=self.name_completer
            ),
            'Other info 1': self.factory_area(
                'Other info 1',
                prefix_min_width=15
            ),
            'Other info 2': self.factory_area(
                'Other info 2',
                prefix_min_width=15
            ),
        }

        self.completion_menu = CompletionsMenu(max_height=16, scroll_offset=1)

        self.float_area = Float(
            xcursor=True,
            ycursor=True,
            content=self.completion_menu,
        )

        self.body = FloatContainer(
            content=HSplit(
                [
                    Window(
                        FormattedTextControl('Ctrl-S - Save and quit | Ctrl-C - Quit without save'),
                        height=1,
                        style="reverse"
                    ),
                    self.text_area['Animal'],
                    self.text_area['Color'],
                    self.text_area['City'],
                    self.text_area['Name'],
                    self.text_area['Other info 1'],
                    self.text_area['Other info 2'],
                ]
            ),
            floats=[
                self.float_area,
            ],
        )

        # self.application = Application(
        #     layout=Layout(self.body),
        #     key_bindings=kb,
        #     full_screen=True
        # )
        self.application = Application(layout=Layout(self.body), key_bindings=kb)

    def accept_text(self, buf):
        get_app().layout.focus_next()
        buf.complete_state = None
        return True

    def factory_area(self, prefix, prefix_min_width=0, completer=None):
        """Generate a text area component."""
        ta = TextArea(
            multiline=False,
            completer=completer,
            width=D(preferred=40),
            accept_handler=self.accept_text,
            get_line_prefix=lambda lineno,
                wrap_count : prefix + (' ' * (prefix_min_width - len(prefix) - 2)) + ': ',
        )
        ta.control.buffer.name = prefix
        return ta

    def run(self):
        self.application.run()
        if self.finish_event == 'quit':
            print('Quitting without saving')
        elif self.finish_event == 'save':
            for key, item in self.text_area.items():
                print(key, ':', item.text)


def main():
    animals = ["alligator", "crocodile", "bird", "cat", "dog"]
    colors = ["red", "yellow", "green", "blue", "pink"]
    cities = ["Rome", "Paris", "Madrid", "Athene", "Lisbon"]
    names = ["Tullio", "Frank", "Jodi", "Mark"]
    editor = EditMask(animals=animals, colors=colors, cities=cities, names=names)
    editor.run()


if __name__ == "__main__":
    main()
