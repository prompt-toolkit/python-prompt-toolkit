from __future__ import annotations

import socket

from prompt_toolkit.contrib.telnet.protocol import TelnetProtocolParser
from prompt_toolkit.contrib.telnet.server import _ConnectionStdout


def test_connection_stdout_escapes_iac():
    a, b = socket.socketpair()
    try:
        stdout = _ConnectionStdout(a, encoding="latin-1")
        # "\xff\xfc\x01" is IAC WONT ECHO when sent unescaped.
        stdout.write("a\xff\xfc\x01b\n")
        wire = b.recv(1024)
    finally:
        a.close()
        b.close()

    assert wire == b"a\xff\xff\xfc\x01b\r\n"

    data: list[bytes] = []
    commands: list[tuple[bytes, bytes]] = []
    parser = TelnetProtocolParser(data.append, lambda rows, columns: None, print)
    parser.command_received = lambda command, d: commands.append((command, d))
    parser.feed(wire)

    assert b"".join(data) == "a\xff\xfc\x01b\r\n".encode("latin-1")
    assert commands == []
