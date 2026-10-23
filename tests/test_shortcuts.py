from __future__ import annotations

from prompt_toolkit.application.current import get_app, set_app
from prompt_toolkit.shortcuts import print_container
from prompt_toolkit.shortcuts.prompt import (
    CompleteStyle,
    PromptSession,
    _split_multiline_prompt,
)
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


def test_callable_complete_style_can_read_current_buffer():
    complete_style_calls: list[str] = []

    def get_complete_style() -> CompleteStyle:
        text = get_app().current_buffer.text
        complete_style_calls.append(text)
        if text:
            return CompleteStyle.MULTI_COLUMN
        return CompleteStyle.READLINE_LIKE

    session: PromptSession[str] = PromptSession(
        complete_style=get_complete_style, validate_while_typing=False
    )

    # The callable requires an active application, so it should not be called
    # while constructing the session.
    assert complete_style_calls == []

    with set_app(session.app):
        assert session.default_buffer.complete_while_typing() is False

        session.default_buffer.text = "text"
        assert session.default_buffer.complete_while_typing() is True

    assert complete_style_calls == ["", "text"]


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
