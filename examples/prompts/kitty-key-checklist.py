#!/usr/bin/env python
"""
Interactive checklist for Kitty-only key gestures.

prompt_toolkit pushes the Kitty keyboard protocol (flag 1) on startup,
so terminals that implement it (kitty, ghostty, wezterm, foot,
Alacritty, recent iTerm2 with CSI u reporting enabled, …) can
distinguish modifier+Enter, modifier+Tab, modifier+Escape, and
modifier+Backspace combinations that collapse to a single byte on
legacy terminals.

The bottom toolbar lists every such gesture. Press one and its row
turns green. On terminals without the protocol, rows stay grey —
that's the expected fallback, not a bug. Press plain Enter to exit.
"""

from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

KITTY_KEYS: list[tuple[str, str]] = [
    ("c-enter", "Ctrl-Enter"),
    ("s-enter", "Shift-Enter"),
    ("c-s-enter", "Ctrl-Shift-Enter"),
    ("c-tab", "Ctrl-Tab"),
    ("c-s-tab", "Ctrl-Shift-Tab"),
    ("c-escape", "Ctrl-Escape"),
    ("c-s-escape", "Ctrl-Shift-Escape"),
    ("c-backspace", "Ctrl-Backspace"),
    ("s-backspace", "Shift-Backspace"),
    ("c-s-backspace", "Ctrl-Shift-Backspace"),
]


def main():
    pressed: set[str] = set()

    def toolbar():
        lines = [("", "Kitty-only gestures — press each to turn it green:\n")]
        for binding, label in KITTY_KEYS:
            if binding in pressed:
                lines.append(("class:done", f"  [x] {label}\n"))
            else:
                lines.append(("class:todo", f"  [ ] {label}\n"))
        remaining = len(KITTY_KEYS) - len(pressed)
        if remaining:
            lines.append(("", f"\n{remaining} remaining — plain Enter to exit."))
        else:
            lines.append(("class:done", "\nAll gestures recorded. Enter to exit."))
        return lines

    bindings = KeyBindings()

    def make_handler(binding: str):
        def handler(event):
            pressed.add(binding)
            event.app.invalidate()

        return handler

    for binding, _label in KITTY_KEYS:
        bindings.add(binding)(make_handler(binding))

    style = Style.from_dict(
        {
            "bottom-toolbar": "noreverse",
            "bottom-toolbar.text": "",
            "done": "fg:ansigreen bold",
            "todo": "fg:ansibrightblack",
        }
    )

    prompt(
        "> ",
        bottom_toolbar=toolbar,
        key_bindings=bindings,
        style=style,
        refresh_interval=0.5,
    )


if __name__ == "__main__":
    main()
