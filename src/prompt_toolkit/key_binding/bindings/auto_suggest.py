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


@Condition
def suggestion_available() -> bool:
    app = get_app()
    buffer = app.current_buffer
    document = buffer.document

    return (
        buffer.suggestion is not None
        and len(buffer.suggestion.text) > 0
        and (
            document.is_cursor_at_the_end
            or (
                vi_navigation_mode()
                and document.cursor_position_row == document.line_count - 1
                and document.cursor_position_col == len(document.current_line) - 1
            )
        )
    )


def load_auto_suggest_bindings() -> KeyBindings:
    """
    Key bindings for accepting auto suggestion text.

    (This has to come after the Vi bindings, because they also have an
    implementation for the "right arrow", but we really want the suggestion
    binding when a suggestion is available.)
    """
    key_bindings = KeyBindings()
    handle = key_bindings.add

    @handle("l", filter=suggestion_available & vi_navigation_mode)
    @handle("c-f", filter=suggestion_available)
    @handle("c-e", filter=suggestion_available)
    @handle("right", filter=suggestion_available)
    def _accept(event: E) -> None:
        """
        Accept suggestion.
        """
        b = event.current_buffer
        suggestion = b.suggestion

        if suggestion:
            if vi_navigation_mode():
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
