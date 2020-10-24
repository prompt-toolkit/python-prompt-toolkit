import pytest

from prompt_toolkit.application import Application, get_app, handle_exit_on_key
from prompt_toolkit.application.current import set_app
from prompt_toolkit.key_binding.key_bindings import KeyBindings, _parse_key
from prompt_toolkit.keys import Keys
from test_key_binding import handlers, set_dummy_app


def test_exit_on_key_simple():
    """
    Setting 'exit_on_key' should create a Binding in 'key_binding'
    """
    with set_dummy_app(exit_on_key="c-c"):
        exit_kb = KeyBindings()
        exit_kb.add("c-c")(handle_exit_on_key)

        app = get_app()

        assert len(app.key_bindings.bindings) == 1

        app_binding = app.key_bindings.bindings[0]
        exit_binding = exit_kb.bindings[0]

        assert app_binding.keys == exit_binding.keys
        assert app_binding.handler == exit_binding.handler


def test_without_exit_on_key():
    """
    Ommiting 'exit_on_key' should leave 'key_binding' unmodified
    """
    kb = KeyBindings()

    @kb.add("c-d")
    def bind(e):
        pass

    with set_dummy_app(key_bindings=kb):
        app = get_app()

        assert app.exit_on_key is None
        assert len(app.key_bindings.bindings) == 1

        app_binding = app.key_bindings.bindings[0]

        assert app_binding.keys == (_parse_key("c-d"),)
        assert app_binding.handler == bind


def test_exit_on_key_not_override(handlers):
    """
    'exit_on_key' should NOT override a 'key_bindings' Binding with same keys
    """
    kb = KeyBindings()
    kb.add("c-c")(handlers.control_c)

    with set_dummy_app(exit_on_key="c-c", key_bindings=kb):
        app = get_app()

        assert len(app.key_bindings.bindings) == 2

        app_last_binding = app.key_bindings.bindings[-1]
        key_bindings_arg = kb.bindings[0]

        # The last binding should be the one we passed in the key_bindings arg,
        # not the one in exit_on_bind
        assert app_last_binding.keys == key_bindings_arg.keys
        assert app_last_binding.handler == key_bindings_arg.handler


def test_exit_on_key_mixed_bindings():
    """
    'exit_on_key' should not interfere with other 'key_bindings' Bindings
    """
    kb = KeyBindings()

    @kb.add("c-d")
    def bind_c_d(event):
        pass

    @kb.add("s-tab")
    def bind_s_tab(event):
        pass

    with set_dummy_app(exit_on_key="c-c", key_bindings=kb):
        app = get_app()

        binding_tuples = [
            (binding.keys, binding.handler) for binding in app.key_bindings.bindings
        ]

        assert len(binding_tuples) == 3
        assert ((_parse_key("c-c"),), handle_exit_on_key) in binding_tuples
        assert ((_parse_key("c-d"),), bind_c_d) in binding_tuples
        assert ((_parse_key("s-tab"),), bind_s_tab) in binding_tuples
