#!/usr/bin/env python
"""
Example of a frame around a prompt input that has autocompletion and a bottom
toolbar.
"""

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style

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


def main():
    style = Style.from_dict(
        {
            "frame.border": "#ff4444",
            "accepted frame.border": "#444444",
        }
    )
    text = prompt(
        "Give some animals: ",
        completer=animal_completer,
        complete_while_typing=False,
        show_frame=True,
        style=style,
        bottom_toolbar="Press [Tab] to complete the current word.",
    )
    print(f"You said: {text}")


if __name__ == "__main__":
    main()
