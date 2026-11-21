from __future__ import annotations

import pytest

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import choice, print_container
from prompt_toolkit.shortcuts.choice_input import ChoiceInput
from prompt_toolkit.shortcuts.prompt import _split_multiline_prompt
from prompt_toolkit.widgets import Frame, TextArea


@pytest.mark.parametrize(
    ("keys", "options", "expected"),
    [
        ("21\r", {}, "one"),
        ("2\x03", {"accept_on_number": True}, "two"),
        ("91\r", {"accept_on_number": True}, "one"),
        ("\x1b[B\r", {"accept_on_number": True}, "two"),
    ],
)
def test_choice_number(keys, options, expected):
    with (
        create_pipe_input() as inp,
        create_app_session(input=inp, output=DummyOutput()),
    ):
        inp.send_text(keys)
        assert (
            choice("Pick", options=[("one", "First"), ("two", "Second")], **options)
            == expected
        )


def test_choice_with_hidden_numbers():
    with (
        create_pipe_input() as inp,
        create_app_session(input=inp, output=DummyOutput()),
    ):
        inp.send_text("2\r")
        result = ChoiceInput(
            message="Pick",
            options=[("one", "First"), ("two", "Second")],
            show_numbers=False,
            accept_on_number=True,
        ).prompt()
        assert result == "one"


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
