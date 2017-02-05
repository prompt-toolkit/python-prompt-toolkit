from __future__ import unicode_literals
from ..utils import is_windows

__all__ = (
    'create_input',
)

def create_input(stdin):
    if is_windows():
        from .win32 import Win32Input
        return Win32Input(stdin)
    else:
        from .vt100 import Vt100Input
        return Vt100Input(stdin)
