from __future__ import annotations

from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys

__all__ = [
    "focus_next",
    "focus_previous",
    "load_focus_bindings",
]

E = KeyPressEvent


def focus_next(event: E) -> None:
    """
    Focus the next visible Window.
    (Often bound to the `Tab` key.)
    """
    event.app.layout.focus_next()


def focus_previous(event: E) -> None:
    """
    Focus the previous visible Window.
    (Often bound to the `BackTab` key.)
    """
    event.app.layout.focus_previous()


def load_focus_bindings() -> KeyBindings:
    """Key bindings for terminal focus events."""
    key_bindings = KeyBindings()

    @key_bindings.add(Keys.FocusIn, save_before=lambda e: False)
    def _(event: E) -> None:
        """Redraw the application after the terminal restores its screen."""
        event.app.renderer.erase(leave_alternate_screen=False)
        event.app.invalidate()

    @key_bindings.add(Keys.FocusOut, save_before=lambda e: False)
    def _(event: E) -> None:
        """Consume the focus-out event."""

    return key_bindings
