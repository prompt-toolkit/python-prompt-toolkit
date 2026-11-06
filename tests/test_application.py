import sys
import types
from unittest.mock import Mock

import pytest

from prompt_toolkit.application import Application
from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput


@pytest.mark.parametrize("value", [None, ""])
def test_default_breakpointhook(value, monkeypatch):
    if value is None:
        monkeypatch.delenv("PYTHONBREAKPOINT", raising=False)
    else:
        monkeypatch.setenv("PYTHONBREAKPOINT", value)
    monkeypatch.setattr(sys, "breakpointhook", sys.__breakpointhook__)
    app = Application(input=DummyInput(), output=DummyOutput())

    with app._enable_breakpointhook():
        assert sys.breakpointhook == app._breakpointhook

    assert sys.breakpointhook is sys.__breakpointhook__


@pytest.mark.parametrize("value", ["0", "custom_debugger.hook"])
def test_environment_breakpointhook(value, monkeypatch):
    monkeypatch.setenv("PYTHONBREAKPOINT", value)
    monkeypatch.setattr(sys, "breakpointhook", sys.__breakpointhook__)
    app = Application(input=DummyInput(), output=DummyOutput())

    with app._enable_breakpointhook():
        assert sys.breakpointhook is sys.__breakpointhook__

    assert sys.breakpointhook is sys.__breakpointhook__


@pytest.mark.parametrize("value", ["", "0", "custom_debugger.hook"])
def test_custom_breakpointhook(value, monkeypatch):
    monkeypatch.setenv("PYTHONBREAKPOINT", value)
    hook = Mock()
    monkeypatch.setattr(sys, "breakpointhook", hook)
    app = Application(input=DummyInput(), output=DummyOutput())

    with app._enable_breakpointhook():
        assert sys.breakpointhook is hook

    assert sys.breakpointhook is hook


def test_breakpointhook_restored_after_exception(monkeypatch):
    monkeypatch.delenv("PYTHONBREAKPOINT", raising=False)
    monkeypatch.setattr(sys, "breakpointhook", sys.__breakpointhook__)
    app = Application(input=DummyInput(), output=DummyOutput())

    with pytest.raises(RuntimeError, match="test exception"):
        with app._enable_breakpointhook():
            assert sys.breakpointhook == app._breakpointhook
            raise RuntimeError("test exception")

    assert sys.breakpointhook is sys.__breakpointhook__


def test_breakpoint_calls_environment_hook(monkeypatch):
    module = types.ModuleType("custom_debugger")
    hook = Mock(return_value="debugger result")
    module.hook = hook
    monkeypatch.setitem(sys.modules, "custom_debugger", module)
    monkeypatch.setenv("PYTHONBREAKPOINT", "custom_debugger.hook")
    monkeypatch.setattr(sys, "breakpointhook", sys.__breakpointhook__)
    app = Application(input=DummyInput(), output=DummyOutput())

    with app._enable_breakpointhook():
        assert sys.breakpointhook is sys.__breakpointhook__
        assert breakpoint("argument", keyword=True) == "debugger result"  # noqa: T100

    hook.assert_called_once_with("argument", keyword=True)
