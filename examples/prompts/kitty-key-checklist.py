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

Pass ``--no-kitty`` to suppress the protocol push so you can verify
that, without it, the gestures are indistinguishable from their legacy
equivalents and the rows stay grey — useful for reproducing how the
prompt behaves on a terminal that doesn't implement the protocol,
from inside one that does.
"""

import argparse

from prompt_toolkit import PromptSession
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
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--no-kitty",
        action="store_true",
        help=(
            "Don't push the Kitty keyboard protocol. Modified keys then "
            "arrive as their legacy single-byte equivalents and the bindings "
            "in this example never fire — useful to verify the non-Kitty "
            "fallback from a Kitty-capable terminal."
        ),
    )
    args = parser.parse_args()

    pressed: set[str] = set()

    def toolbar():
        header = (
            "Kitty protocol DISABLED (--no-kitty) — rows stay grey:\n"
            if args.no_kitty
            else "Kitty-only gestures — press each to turn it green:\n"
        )
        lines = [("", header)]
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

    session = PromptSession(
        "> ",
        bottom_toolbar=toolbar,
        key_bindings=bindings,
        style=style,
        refresh_interval=0.5,
    )

    if args.no_kitty:
        # Short-circuit the renderer's one-shot push/query block by
        # flipping its "already pushed" flag so the conditional at the
        # top of Renderer.render() skips both the push and the probe.
        # We hook `Application.on_reset` rather than setting the flag
        # directly — `Application.run()` calls `renderer.reset()`
        # first, which would clear a pre-set flag; `on_reset` fires
        # *after* that reset and before the first render, which is the
        # window we need. Reaching into the private attribute is fine
        # for a demo; there is no public "disable kitty" knob on
        # Application/Renderer today.
        def _suppress_kitty(_app):
            session.app.renderer._kitty_keyboard_pushed = True

        session.app.on_reset += _suppress_kitty

    session.prompt()


if __name__ == "__main__":
    main()
