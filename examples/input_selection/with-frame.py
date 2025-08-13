from __future__ import annotations

from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts.input_selection import select_input
from prompt_toolkit.styles import Style


def main() -> None:
    style = Style.from_dict(
        {
            "frame.border": "#884444",
        }
    )

    result = select_input(
        message=HTML("<u>Please select a dish</u>:"),
        options=[
            ("pizza", "Pizza with mushrooms"),
            ("salad", "Salad with tomatoes"),
            ("sushi", "Sushi"),
        ],
        style=style,
        show_frame=1,
    )
    print(result)


if __name__ == "__main__":
    main()
