from __future__ import annotations

from prompt_toolkit.filters import is_done
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.styles import Style


def main() -> None:
    style = Style.from_dict(
        {
            "frame.border": "#884444",
            "selected-option": "bold underline",
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
        # Use `~is_done`, if you only want to show the frame while editing and
        # hide it when the input is accepted.
        # Use `True`, if you always want to show the frame.
        show_frame=~is_done,
    )
    print(result)


if __name__ == "__main__":
    main()
