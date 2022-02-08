#!/usr/bin/env python
from __future__ import unicode_literals
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import ANSI, HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    FormattedTextControl,
    HSplit,
    Layout,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.widgets import Dialog, Label, TextArea


def main():
    # Key bindings.
    kb = KeyBindings()

    @kb.add("c-c")
    def _(event):
        "Quit when control-c is pressed."
        event.app.exit()

    text_area = TextArea(text="You can type here...")
    dialog_body = HSplit(
        [
            Label(
                HTML("Press <reverse>control-c</reverse> to quit."),
                align=WindowAlign.CENTER,
            ),
            VSplit(
                [
                    Label(PROMPT_TOOLKIT_LOGO, align=WindowAlign.CENTER),
                    text_area,
                ],
            ),
        ]
    )

    application = Application(
        layout=Layout(
            container=Dialog(
                title="ANSI Art demo - Art on the left, text area on the right",
                body=dialog_body,
                with_background=True,
            ),
            focused_element=text_area,
        ),
        full_screen=True,
        mouse_support=True,
        key_bindings=kb,
    )
    application.run()

logo_txt = Path(__file__).parent / "ansi-logos" / "pt-logo-48x48-24bit.txt"

PROMPT_TOOLKIT_LOGO = ANSI(logo_txt.read_text())

if __name__ == "__main__":
    main()
