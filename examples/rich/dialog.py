#!/usr/bin/env python
"""
Example of an input box dialog.
"""

from rich.text import Text

from prompt_toolkit.shortcuts import input_dialog


def main():
    result = input_dialog(
        title=Text.from_markup("[red]Input[/red] dialog [b]example[b]"),
        text=Text.from_markup("Please type your [green]name[/green]:"),
    ).run()

    print(f"Result = {result}")


if __name__ == "__main__":
    main()
