#!/usr/bin/env python
"""Choose several dishes without opening a full-screen dialog."""

from __future__ import annotations

from prompt_toolkit.shortcuts import choice


def main() -> None:
    dishes = choice(
        message="Please choose your dishes:",
        options=[
            ("pizza", "Pizza with mushrooms"),
            ("salad", "Salad with tomatoes"),
            ("sushi", "Sushi"),
        ],
        multiple_selection=True,
        default_values=["salad"],
        bottom_toolbar=" Up/Down: move  Space: toggle  Enter: accept",
    )
    print(f"You have chosen: {dishes}")


if __name__ == "__main__":
    main()
