#!/usr/bin/env python
"""
This will display a prompt that will always use the terminal for input and
output, even if sys.stdin/stdout are connected to pipes.

For testing, run as:
    cat /dev/null | python ./enforce-tty-input-output.py > /dev/null
"""
from prompt_toolkit.application import create_app_session_from_tty
from prompt_toolkit.shortcuts import prompt

with create_app_session_from_tty():
    prompt(">")
