"""
Helpers for the Kitty keyboard protocol (output side).

Ref: https://sw.kovidgoyal.net/kitty/keyboard-protocol/

The protocol exposes progressive enhancement flags that a program pushes
onto a terminal-maintained stack, then pops on exit:

    CSI > <flags> u        — push <flags> onto the stack
    CSI < u                — pop one entry
    CSI ? u                — query current flags (response: CSI ? <flags> u)

(`CSI = <flags> ; <mode> u` also exists — it *modifies* the top of the
stack in place rather than pushing. We want a clean restore on exit, so
we push.)

Flag bits (from the spec):

    0b1     (1)   Disambiguate escape codes
    0b10    (2)   Report event types (press/release/repeat)
    0b100   (4)   Report alternate keys
    0b1000  (8)   Report all keys as escape codes
    0b10000 (16)  Report associated text

Currently uses only `disambiguate` (flag 1). That's enough to get Ctrl-Enter
and friends while leaving plain printable / Shifted keys reporting as
legacy bytes — so no parser additions are needed for input the terminal
doesn't rewrite.

The terminal itself maintains the flags stack, so nested `with` blocks
compose correctly at the wire level. We still track a local depth
counter per `Output` instance (and the currently-active flag value) so
we can raise on a nested call that would change the flags, rather than
silently corrupt the terminal's stack.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Output


__all__ = [
    "KITTY_FLAG_DISAMBIGUATE",
    "KITTY_FLAG_REPORT_EVENT_TYPES",
    "KITTY_FLAG_REPORT_ALTERNATE_KEYS",
    "KITTY_FLAG_REPORT_ALL_KEYS",
    "KITTY_FLAG_REPORT_TEXT",
    "KITTY_QUERY",
    "kitty_keyboard_protocol",
]


KITTY_FLAG_DISAMBIGUATE = 0b00001
KITTY_FLAG_REPORT_EVENT_TYPES = 0b00010
KITTY_FLAG_REPORT_ALTERNATE_KEYS = 0b00100
KITTY_FLAG_REPORT_ALL_KEYS = 0b01000
KITTY_FLAG_REPORT_TEXT = 0b10000


# Sent to detect protocol support; terminal answers `CSI ? <flags> u` if
# supported, silence if not.
KITTY_QUERY = "\x1b[?u"


@contextmanager
def kitty_keyboard_protocol(
    output: Output, flags: int = KITTY_FLAG_DISAMBIGUATE
) -> Iterator[None]:
    """
    Push the given Kitty keyboard flags on entry, pop on exit.

    Nested blocks on the same `Output` share the push/pop pair — only
    the outermost enter writes the enable sequence and only the
    outermost exit writes the pop. Each enter/exit calls
    ``output.flush()`` so a caller can rely on the sequence having
    actually reached the terminal before waiting for input (e.g. for
    the `CSI ? u` query response).

    A nested call must use the same `flags` as the outer one. Mixing
    flags would leave the terminal in a state the inner caller didn't
    ask for, and the inner pop would cancel the outer push; we raise
    `ValueError` rather than silently corrupt the stack.
    """
    # Lazily install counter + flags state on the Output. We do it here
    # rather than on Output.__init__ so this module stays fully
    # self-contained and the rest of the codebase has no mention of it.
    depth: int = getattr(output, "_kitty_keyboard_depth", 0)
    if depth == 0:
        # Push: `CSI > <flags> u`.
        output.write_raw(f"\x1b[>{flags}u")
        output.flush()
        output._kitty_keyboard_flags = flags  # type: ignore[attr-defined]
    else:
        active = getattr(output, "_kitty_keyboard_flags", flags)
        if active != flags:
            raise ValueError(
                f"kitty_keyboard_protocol already entered with flags="
                f"{active!r}; nested call requested flags={flags!r}. "
                f"Mixing flags across nested contexts is unsupported."
            )
    output._kitty_keyboard_depth = depth + 1  # type: ignore[attr-defined]
    try:
        yield
    finally:
        output._kitty_keyboard_depth -= 1  # type: ignore[attr-defined]
        if output._kitty_keyboard_depth == 0:  # type: ignore[attr-defined]
            # Pop one entry off the terminal's flag stack.
            output.write_raw("\x1b[<u")
            output.flush()
