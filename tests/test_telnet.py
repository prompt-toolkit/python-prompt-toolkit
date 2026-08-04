from __future__ import annotations

from unittest.mock import Mock

import prompt_toolkit.contrib.telnet.server as telnet_server
from prompt_toolkit.contrib.telnet.server import TelnetConnection


def _create_connection() -> TelnetConnection:
    connection = object.__new__(TelnetConnection)
    connection.conn = Mock()
    connection.addr = ("127.0.0.1", 1234)
    connection.parser = Mock()
    connection.vt100_input = Mock()
    connection.stdout = Mock()
    connection._closed = False
    return connection


def test_handle_incoming_data() -> None:
    connection = _create_connection()
    connection.conn.recv.return_value = b"hello"

    connection._handle_incoming_data()

    connection.parser.feed.assert_called_once_with(b"hello")
    assert not connection._closed


def test_handle_incoming_data_eof(monkeypatch) -> None:
    connection = _create_connection()
    connection.conn.recv.return_value = b""
    loop = Mock()
    monkeypatch.setattr(telnet_server, "get_running_loop", lambda: loop)

    connection._handle_incoming_data()

    assert connection._closed
    loop.remove_reader.assert_called_once_with(connection.conn)
    connection.conn.close.assert_called_once_with()


def test_handle_incoming_data_connection_reset(monkeypatch) -> None:
    connection = _create_connection()
    connection.conn.recv.side_effect = ConnectionResetError(104, "Connection reset")
    loop = Mock()
    monkeypatch.setattr(telnet_server, "get_running_loop", lambda: loop)

    connection._handle_incoming_data()

    assert connection._closed
    loop.remove_reader.assert_called_once_with(connection.conn)
    connection.conn.close.assert_called_once_with()
