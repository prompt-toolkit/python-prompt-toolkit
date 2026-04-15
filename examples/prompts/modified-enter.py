#!/usr/bin/env python
"""
Demo for modified-Enter key bindings (Ctrl-Enter, Ctrl-Shift-Enter,
Shift-Enter).

prompt_toolkit pushes the Kitty keyboard protocol (flag 1) on startup,
so terminals that implement it (kitty, ghostty, wezterm, foot,
Alacritty, recent iTerm2 with CSI u reporting enabled, …) can
distinguish these from plain Enter.

Run this and try pressing each combination. Plain Enter still submits
(the `c-m` / `enter` binding shipped by ``PromptSession`` defaults
fires as usual — our custom bindings below don't override it).
Terminals that don't support the protocol will just submit on any Enter
variant — that's the expected fallback.
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

    @bindings.add("s-enter")
    def _(event):
        _announce("Shift-Enter")

    @bindings.add("c-s-enter")
    def _(event):
        _announce("Ctrl-Shift-Enter")

    print("Try Ctrl-Enter, Shift-Enter, Ctrl-Shift-Enter. Plain Enter submits.")
    text = prompt("> ", key_bindings=bindings)
    print(f"You said: {text!r}")


if __name__ == "__main__":
    main()
