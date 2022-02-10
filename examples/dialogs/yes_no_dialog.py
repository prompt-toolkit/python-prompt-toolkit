#!/usr/bin/env python
"""
Example of confirmation (yes/no) dialog window.
"""
from prompt_toolkit.shortcuts import yes_no_dialog


def main():
    result = yes_no_dialog(
        title="Yes/No dialog example", text="Do you want to confirm?"
    ).run()

    print(f"Result = {result}")


if __name__ == "__main__":
    main()
