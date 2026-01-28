from __future__ import annotations

from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.styles import Style


def main() -> None:
    style = Style.from_dict(
        {
            "input-selection": "fg:#ff0000",
            "number": "fg:#884444 bold",
            "selected-option": "underline",
            "frame.border": "#884444",
        }
    )

    result = choice(
        message=HTML("<u>Please select a dish</u>:"),
        options=[
            ("pizza", "Pizza with mushrooms"),
            (
                "salad",
                HTML("<ansigreen>Salad</ansigreen> with <ansired>tomatoes</ansired>"),
            ),
            ("sushi", "Sushi"),
        ],
        style=style,
    )
    print(result)


if __name__ == "__main__":
    main()
