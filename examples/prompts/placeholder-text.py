#!/usr/bin/env python
"""
Example of a placeholer that's displayed as long as no input is given.
"""
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML

if __name__ == "__main__":
    answer = prompt(
        "Give me some input: ",
        placeholder=HTML('<style color="#888888">(please type something)</style>'),
    )
    print("You said: %s" % answer)
