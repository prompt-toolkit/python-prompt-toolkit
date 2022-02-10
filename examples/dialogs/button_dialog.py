#!/usr/bin/env python
"""
Example of button dialog window.
"""
from prompt_toolkit.shortcuts import button_dialog


def main():
    result = button_dialog(
        title="Button dialog example",
        text="Are you sure?",
        buttons=[("Yes", True), ("No", False), ("Maybe...", None)],
    ).run()

    print(f"Result = {result}")


if __name__ == "__main__":
    main()
