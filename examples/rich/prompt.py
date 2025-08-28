#!/usr/bin/env python
from rich.text import Text

from prompt_toolkit import prompt


def main():
    answer = prompt(Text.from_markup("[green]Say[/green] [b]something[/b] > "))
    print(f"You said: {answer}")


if __name__ == "__main__":
    main()
