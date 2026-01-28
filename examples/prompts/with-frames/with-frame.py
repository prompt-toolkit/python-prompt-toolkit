#!/usr/bin/env python
"""
Example of a frame around a prompt input.
"""

from prompt_toolkit import prompt
from prompt_toolkit.styles import Style

style = Style.from_dict(
    {
        "frame.border": "#884444",
    }
)


def example():
    """
    Style and list of (style, text) tuples.
    """
    answer = prompt("Say something > ", style=style, show_frame=True)
    print(f"You said: {answer}")


if __name__ == "__main__":
    example()
