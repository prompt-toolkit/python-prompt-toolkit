#!/usr/bin/env python
"""
Example that displays how to switch between Emacs and Vi input mode.

"""
from prompt_toolkit import prompt
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.key_binding.registry import Registry
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.token import Token

def run():
    # Create a `Registry` that contains the default key bindings.
    registry = Registry()

    # Add an additional key binding for toggling this flag.
    @registry.add_binding(Keys.F4)
    def _(event):
        " Toggle between Emacs and Vi mode. "
        if event.app.editing_mode == EditingMode.VI:
            event.app.editing_mode = EditingMode.EMACS
        else:
            event.app.editing_mode = EditingMode.VI

    # Add a bottom toolbar to display the status.
    style = style_from_dict({
        Token.Toolbar: 'reverse',
    })

    def get_bottom_toolbar_tokens(app):
        " Display the current input mode. "
        text = 'Vi' if app.editing_mode == EditingMode.VI else 'Emacs'
        return [
            (Token.Toolbar, ' [F4] %s ' % text)
        ]

    prompt('> ', extra_key_bindings=registry,
           get_bottom_toolbar_tokens=get_bottom_toolbar_tokens,
           style=style)


if __name__ == '__main__':
    run()
