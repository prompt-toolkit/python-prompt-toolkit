#!/usr/bin/env python
"""
Example of a call to `prompt` with a default value.
The input is pre-filled, but the user can still edit the default.
"""

import getpass

from prompt_toolkit import prompt

if __name__ == "__main__":
    answer = prompt("What is your name: ", default=f"{getpass.getuser()}")
    print(f"You said: {answer}")
