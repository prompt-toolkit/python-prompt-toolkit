from __future__ import annotations

from prompt_toolkit.shortcuts.input_selection import select_input


def main() -> None:
    result = select_input(
        message="Please select a dish:",
        options=[
            ("pizza", "Pizza with mushrooms"),
            ("salad", "Salad with tomatoes"),
            ("sushi", "Sushi"),
        ],
    )
    print(result)


if __name__ == "__main__":
    main()
