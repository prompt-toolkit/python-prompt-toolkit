#!/usr/bin/env python
""" 
Prompt for user input as a toolbar which disappears after submission.
"""
from prompt_toolkit import prompt

if __name__ == "__main__":
    answer = prompt(message="prompt$ ", prompt_in_toolbar=True)
    print(f"You said: {answer}")
