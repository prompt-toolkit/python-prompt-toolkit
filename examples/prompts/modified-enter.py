#!/usr/bin/env python
"""
Demo for modified-Enter key bindings (Ctrl-Enter and Ctrl-Shift-Enter).

prompt_toolkit enables xterm's `modifyOtherKeys` protocol at startup, so
terminals that implement it (xterm, iTerm2 with the option enabled, kitty,
WezTerm, Alacritty, foot, ghostty, Windows Terminal, ...) can distinguish
these from plain Enter.

Run this and try pressing each combination. Plain Enter still submits.
Terminals that don't support the protocol will just submit on any Enter
variant — that's the expected fallback.

Shift-Enter alone is not included: many terminals that support
modifyOtherKeys still send plain '\\r' for it, so a binding would fire
inconsistently.
"""

from prompt_toolkit import prompt
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.key_binding import KeyBindings


def main():
    bindings = KeyBindings()

    def _announce(label):
        def _print():
            print(f"[{label}] pressed")

        run_in_terminal(_print)

    @bindings.add("c-enter")
    def _(event):
        _announce("Ctrl-Enter")

    @bindings.add("c-s-enter")
    def _(event):
        _announce("Ctrl-Shift-Enter")

    print("Try Ctrl-Enter and Ctrl-Shift-Enter. Plain Enter submits.")
    text = prompt("> ", key_bindings=bindings)
    print(f"You said: {text!r}")


if __name__ == "__main__":
    main()
