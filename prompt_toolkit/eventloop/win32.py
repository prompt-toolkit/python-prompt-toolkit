from ctypes import pointer, windll
from ctypes.wintypes import BOOL, DWORD, HANDLE
from typing import List, Optional

from prompt_toolkit.win32_types import SECURITY_ATTRIBUTES

__all__ = [
    'wait_for_handles',
    'create_win32_event'
]


WAIT_TIMEOUT = 0x00000102
INFINITE = -1


def wait_for_handles(handles: List[int], timeout: int = INFINITE) -> Optional[HANDLE]:
    """
    Waits for multiple handles. (Similar to 'select') Returns the handle which is ready.
    Returns `None` on timeout.
    http://msdn.microsoft.com/en-us/library/windows/desktop/ms687025(v=vs.85).aspx
    """
    arrtype = HANDLE * len(handles)
    handle_array = arrtype(*handles)

    ret = windll.kernel32.WaitForMultipleObjects(
        len(handle_array), handle_array, BOOL(False), DWORD(timeout))

    if ret == WAIT_TIMEOUT:
        return None
    else:
        h = handle_array[ret]
        return h


def create_win32_event():
    """
    Creates a Win32 unnamed Event .
    http://msdn.microsoft.com/en-us/library/windows/desktop/ms682396(v=vs.85).aspx
    """
    return windll.kernel32.CreateEventA(
        pointer(SECURITY_ATTRIBUTES()),
        BOOL(True),  # Manual reset event.
        BOOL(False),  # Initial state.
        None  # Unnamed event object.
    )
