from __future__ import annotations

from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.styles import Style


def main() -> None:
    style = Style.from_dict(
        {
            "selected-option": "bold",
            "frame.border": "#ff4444",
            "accepted frame.border": "#888888",
        }
    )

    result = choice(
        message=HTML("<u>Please select a dish</u>:"),
        options=[
            ("pizza", "Pizza with mushrooms"),
            ("salad", "Salad with tomatoes"),
            ("sushi", "Sushi"),
        ],
        style=style,
        show_frame=True,
    )
    print(result)


if __name__ == "__main__":
    main()
