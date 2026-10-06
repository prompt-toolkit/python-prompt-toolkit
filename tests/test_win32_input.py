from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


def test_vt100_console_input_reader_combines_surrogate_pairs(monkeypatch):
    from prompt_toolkit.input import win32

    # U+1F132 is sent by the console as two key events: a high and a low
    # UTF-16 surrogate.
    units = ["a", "\ud83c", "\udd32", "b"]

    class FakeKernel32:
        def GetStdHandle(self, handle):
            return 0

        def ReadConsoleInputW(self, handle, records, max_count, read):
            for i, unit in enumerate(units):
                record = records.contents[i]
                record.EventType = 1  # KEY_EVENT
                record.Event.KeyEvent.KeyDown = 1
                record.Event.KeyEvent.uChar.UnicodeChar = unit
            read.contents.value = len(units)

    class FakeWindll:
        kernel32 = FakeKernel32()

    class FakeStdin:
        def isatty(self):
            return True

    monkeypatch.setattr(win32, "windll", FakeWindll())
    monkeypatch.setattr(win32, "wait_for_handles", lambda handles, timeout: True)
    monkeypatch.setattr(sys, "stdin", FakeStdin())

    reader = win32.Vt100ConsoleInputReader()
    keys = list(reader.read()) + reader.flush_keys()

    assert [key.key for key in keys] == ["a", "\U0001f132", "b"]
