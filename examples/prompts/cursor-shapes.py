#!/usr/bin/env python
"""
Example of cursor shape configurations.
"""
from prompt_toolkit import prompt
from prompt_toolkit.cursor_shapes import CursorShape, ModalCursorShapeConfig

# NOTE: We pass `enable_suspend=True`, so that we can easily see what happens
#       to the cursor shapes when the application is suspended.

prompt("(block): ", cursor=CursorShape.BLOCK, enable_suspend=True)
prompt("(underline): ", cursor=CursorShape.UNDERLINE, enable_suspend=True)
prompt("(beam): ", cursor=CursorShape.BEAM, enable_suspend=True)
prompt(
    "(modal - according to vi input mode): ",
    cursor=ModalCursorShapeConfig(),
    vi_mode=True,
    enable_suspend=True,
)
