"""
Key bindings for auto suggestion (for fish-style auto suggestion).
"""

from __future__ import annotations

import re

from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import Condition, emacs_mode, vi_navigation_mode
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

__all__ = [
    "load_auto_suggest_bindings",
]

E = KeyPressEvent


def load_auto_suggest_bindings() -> KeyBindings:
    """
    Key bindings for accepting auto suggestion text.

    (This has to come after the Vi bindings, because they also have an
    implementation for the "right arrow", but we really want the suggestion
    binding when a suggestion is available.)
    """
    key_bindings = KeyBindings()
    handle = key_bindings.add

    @Condition
    def suggestion_available() -> bool:
        app = get_app()
        return (
            app.current_buffer.suggestion is not None
            and len(app.current_buffer.suggestion.text) > 0
            and app.current_buffer.document.is_cursor_at_the_end
        )

    @Condition
    def suggestion_available_vi_navigation() -> bool:
        # In Vi navigation mode, the cursor can never move past the last
        # character (unlike insert mode), so `is_cursor_at_the_end` can
        # never be true for a non-empty buffer. Being on the last character
        # is the navigation-mode equivalent of "at the end" here.
        app = get_app()
        buffer = app.current_buffer
        document = buffer.document
        return (
            buffer.suggestion is not None
            and len(buffer.suggestion.text) > 0
            and document.cursor_position >= len(document.text) - 1
        )

    @handle("c-f", filter=suggestion_available)
    @handle("c-e", filter=suggestion_available)
    @handle("right", filter=suggestion_available)
    @handle("l", filter=suggestion_available_vi_navigation & vi_navigation_mode)
    def _accept(event: E) -> None:
        """
        Accept suggestion.
        """
        b = event.current_buffer
        suggestion = b.suggestion

        if suggestion:
            # In Vi navigation mode the cursor sits *on* the last character
            # rather than past it, so move to the true end before inserting,
            # otherwise the suggestion would be spliced in before that
            # character instead of appended.
            b.cursor_position = len(b.text)
            b.insert_text(suggestion.text)

    @handle("escape", "f", filter=suggestion_available & emacs_mode)
    def _fill(event: E) -> None:
        """
        Fill partial suggestion.
        """
        b = event.current_buffer
        suggestion = b.suggestion

        if suggestion:
            t = re.split(r"([^\s/]+(?:\s+|/))", suggestion.text)
            b.insert_text(next(x for x in t if x))

    return key_bindings
