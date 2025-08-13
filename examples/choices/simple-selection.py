from __future__ import annotations

from prompt_toolkit.shortcuts import choice


def main() -> None:
    result = choice(
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
