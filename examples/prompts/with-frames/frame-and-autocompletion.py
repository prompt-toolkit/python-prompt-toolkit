#!/usr/bin/env python
"""
Example of a frame around a prompt input that has autocompletion and a bottom
toolbar.
"""

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.filters import is_done

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
    text = prompt(
        "Give some animals: ",
        completer=animal_completer,
        complete_while_typing=False,
        # Only show the frame during editing. Hide when the input gets accepted.
        show_frame=~is_done,
        bottom_toolbar="Press [Tab] to complete the current word.",
    )
    print(f"You said: {text}")


if __name__ == "__main__":
    main()
