from __future__ import annotations

from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import choice


def main() -> None:
    result = choice(
        message=HTML("<u>Please select a dish</u>:"),
        options=[
            ("pizza", "Pizza with mushrooms"),
            ("salad", "Salad with tomatoes"),
            ("sushi", "Sushi"),
        ],
        mouse_support=True,
    )
    print(result)


if __name__ == "__main__":
    main()
