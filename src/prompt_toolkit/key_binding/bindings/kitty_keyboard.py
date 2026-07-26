"""
Binding that consumes the Kitty keyboard protocol `CSI ? <flags> u`
response and reports the result to the Renderer's capability state.
"""

from __future__ import annotations

from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys

from ..key_bindings import KeyBindings

__all__ = ["load_kitty_keyboard_bindings"]

E = KeyPressEvent


def load_kitty_keyboard_bindings() -> KeyBindings:
    key_bindings = KeyBindings()

    # `eager=True` so this binding pre-empts any catch-all `Keys.Any`
    # binding (e.g. `self_insert` from basic bindings). Without it, a
    # custom KeyBindings setup that omits load_kitty_keyboard_bindings
    # but keeps a Keys.Any handler would inject the raw `\x1b[?1u`
    # response into the buffer.
    @key_bindings.add(
        Keys.KittyKeyboardResponse, eager=True, save_before=lambda e: False
    )
    def _(event: E) -> None:
        """
        A `CSI ? <flags> u` response came back — the terminal speaks the
        Kitty keyboard protocol. Flip the renderer's capability flag.
        """
        event.app.renderer.report_kitty_keyboard_response()

    return key_bindings
