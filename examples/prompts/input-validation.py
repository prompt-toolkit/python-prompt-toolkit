#!/usr/bin/env python
"""
Simple example of input validation.
"""

from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator


def is_valid_email(text):
    return "@" in text


validator = Validator.from_callable(
    is_valid_email,
    error_message="Not a valid e-mail address (Does not contain an @).",
    move_cursor_to_end=True,
)


def main():
    # Validate when pressing ENTER.
    text = prompt(
        "Enter e-mail address: ", validator=validator, validate_while_typing=False
    )
    print(f"You said: {text}")

    # While typing
    text = prompt(
        "Enter e-mail address: ", validator=validator, validate_while_typing=True
    )
    print(f"You said: {text}")


if __name__ == "__main__":
    main()
