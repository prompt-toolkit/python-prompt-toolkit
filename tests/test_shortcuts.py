from __future__ import annotations

from unittest.mock import patch

from prompt_toolkit.shortcuts import print_container
from prompt_toolkit.shortcuts.prompt import PromptSession, _split_multiline_prompt
from prompt_toolkit.widgets import Frame, TextArea


def test_split_multiline_prompt():
    # Test 1: no newlines:
    tokens = [("class:testclass", "ab")]
    has_before_tokens, before, first_input_line = _split_multiline_prompt(
        lambda: tokens
    )
    assert has_before_tokens() is False
    assert before() == []
    assert first_input_line() == [
        ("class:testclass", "a"),
        ("class:testclass", "b"),
    ]

    # Test 1: multiple lines.
    tokens = [("class:testclass", "ab\ncd\nef")]
    has_before_tokens, before, first_input_line = _split_multiline_prompt(
        lambda: tokens
    )
    assert has_before_tokens() is True
    assert before() == [
        ("class:testclass", "a"),
        ("class:testclass", "b"),
        ("class:testclass", "\n"),
        ("class:testclass", "c"),
        ("class:testclass", "d"),
    ]
    assert first_input_line() == [
        ("class:testclass", "e"),
        ("class:testclass", "f"),
    ]

    # Edge case 1: starting with a newline.
    tokens = [("class:testclass", "\nab")]
    has_before_tokens, before, first_input_line = _split_multiline_prompt(
        lambda: tokens
    )
    assert has_before_tokens() is True
    assert before() == []
    assert first_input_line() == [("class:testclass", "a"), ("class:testclass", "b")]

    # Edge case 2: starting with two newlines.
    tokens = [("class:testclass", "\n\nab")]
    has_before_tokens, before, first_input_line = _split_multiline_prompt(
        lambda: tokens
    )
    assert has_before_tokens() is True
    assert before() == [("class:testclass", "\n")]
    assert first_input_line() == [("class:testclass", "a"), ("class:testclass", "b")]


def test_prompt_per_call_override_restore():
    """Per-call kwargs to prompt() should not permanently change session state (#967)."""
    session = PromptSession()

    # Verify defaults.
    assert session.is_password is False
    assert session.multiline is False
    assert session.wrap_lines is True
    assert session.message == ""

    # Call prompt() with overrides. app.run will raise (no terminal), but the
    # finally block should still restore the original values.
    with patch.object(session.app, "run", side_effect=EOFError):
        try:
            session.prompt(
                "test> ",
                is_password=True,
                multiline=True,
                wrap_lines=False,
            )
        except EOFError:
            pass

    # All overridden attributes should be restored.
    assert session.is_password is False
    assert session.multiline is False
    assert session.wrap_lines is True
    assert session.message == ""


def test_print_container(tmpdir):
    # Call `print_container`, render to a dummy file.
    f = tmpdir.join("output")
    with open(f, "w") as fd:
        print_container(Frame(TextArea(text="Hello world!\n"), title="Title"), file=fd)

    # Verify rendered output.
    with open(f) as fd:
        text = fd.read()
        assert "Hello world" in text
        assert "Title" in text
