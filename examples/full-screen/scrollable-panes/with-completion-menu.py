#!/usr/bin/env python
"""
A simple example of a scrollable pane.
"""
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.layout import (
    CompletionsMenu,
    Float,
    FloatContainer,
    HSplit,
    Layout,
    ScrollablePane,
    VSplit,
)
from prompt_toolkit.widgets import Frame, Label, TextArea


def main():
    # Create a big layout of many text areas, then wrap them in a `ScrollablePane`.
    root_container = VSplit(
        [
            Label("<left column>"),
            HSplit(
                [
                    Label("ScrollContainer Demo"),
                    Frame(
                        ScrollablePane(
                            HSplit(
                                [
                                    Frame(
                                        TextArea(
                                            text=f"label-{i}",
                                            completer=animal_completer,
                                        )
                                    )
                                    for i in range(20)
                                ]
                            )
                        ),
                    ),
                ]
            ),
        ]
    )

    root_container = FloatContainer(
        root_container,
        floats=[
            Float(
                xcursor=True,
                ycursor=True,
                content=CompletionsMenu(max_height=16, scroll_offset=1),
            ),
        ],
    )

    layout = Layout(container=root_container)

    # Key bindings.
    kb = KeyBindings()

    @kb.add("c-c")
    def exit(event) -> None:
        get_app().exit()

    kb.add("tab")(focus_next)
    kb.add("s-tab")(focus_previous)

    # Create and run application.
    application = Application(
        layout=layout, key_bindings=kb, full_screen=True, mouse_support=True
    )
    application.run()


animal_completer = WordCompleter(
    [
        "alligator",
        "ant",
        "ape",
        "bat",
        "bear",
        "beaver",
        "bee",
        "bison",
        "butterfly",
        "cat",
        "chicken",
        "crocodile",
        "dinosaur",
        "dog",
        "dolphin",
        "dove",
        "duck",
        "eagle",
        "elephant",
        "fish",
        "goat",
        "gorilla",
        "kangaroo",
        "leopard",
        "lion",
        "mouse",
        "rabbit",
        "rat",
        "snake",
        "spider",
        "turkey",
        "turtle",
    ],
    ignore_case=True,
)


if __name__ == "__main__":
    main()
