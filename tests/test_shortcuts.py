from __future__ import annotations

import pytest

from prompt_toolkit import renderer
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import PromptSession, print_container
from prompt_toolkit.shortcuts.prompt import _split_multiline_prompt
from prompt_toolkit.widgets import Frame, TextArea


@pytest.mark.parametrize(
    "placeholder", ["Type a value", ANSI("\x1b[90mType a value\x1b[0m")]
)
@pytest.mark.parametrize("text", ["", "hello"])
def test_placeholder_is_hidden_after_accepting_input(mocker, placeholder, text):
    draw = mocker.spy(renderer, "_output_screen_diff")
    with create_pipe_input() as inp:
        session = PromptSession(
            "Question: ",
            placeholder=placeholder,
            input=inp,
            output=DummyOutput(),
        )
        inp.send_text(text + "\r")
        assert session.prompt() == text

    # Inspect the actual screens sent to the output, including the final redraw.
    screens = []
    for call in draw.call_args_list:
        screen, is_done = call.args[2], call.args[7]
        content = "\n".join(
            "".join(char.char for _, char in sorted(row.items())).rstrip()
            for _, row in sorted(screen.data_buffer.items())
        ).rstrip()
        screens.append((is_done, content))

    assert any("Type a value" in content for is_done, content in screens if not is_done)
    assert [content for is_done, content in screens if is_done] == [
        ("Question: " + text).rstrip()
    ]


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
