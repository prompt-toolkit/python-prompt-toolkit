from __future__ import annotations

import pytest

from prompt_toolkit.data_structures import Size
from prompt_toolkit.filters import Condition
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import PromptSession, print_container
from prompt_toolkit.shortcuts.prompt import _split_multiline_prompt
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


@pytest.mark.parametrize(
    "message, wrap_lines, expected",
    [
        ("abcdefghijklmnopqrstuv\n> ", True, ["abcdefghij", "klmnopqrst", "uv", "> "]),
        ("abcdefghijklmnopqrstuv\n> ", False, ["abcdefghij", "> "]),
        ("short\n> ", True, ["short", "> "]),
        ("abcdefghij\n> ", True, ["abcdefghij", "> "]),
        (
            "abcdefghijkl\nmnopqrstuvwx\n> ",
            True,
            ["abcdefghij", "kl", "mnopqrstuv", "wx", "> "],
        ),
    ],
)
def test_multiline_prompt_wraps_before_input(message, wrap_lines, expected):
    class SmallOutput(DummyOutput):
        def get_size(self):
            return Size(rows=24, columns=10)

    rendered_lines = []
    with create_pipe_input() as inp:
        session = PromptSession(
            message,
            wrap_lines=wrap_lines,
            input=inp,
            output=SmallOutput(),
            reserve_space_for_menu=0,
        )

        def after_render(app):
            screen = app.renderer._last_screen
            if screen is not None:
                rendered_lines.extend(
                    "".join(screen.data_buffer[y][x].char for x in range(10)).rstrip()
                    for y in range(len(expected))
                )
                app.exit(result="")

        session.app.after_render += after_render
        session.prompt()

    assert rendered_lines == [line.rstrip() for line in expected]


def test_multiline_prompt_wrap_filter_changes_between_calls():
    class SmallOutput(DummyOutput):
        def get_size(self):
            return Size(rows=24, columns=10)

    wrap = False
    rendered_lines = []
    with create_pipe_input() as inp:
        session = PromptSession(
            "abcdefghijkl\n> ",
            wrap_lines=Condition(lambda: wrap),
            input=inp,
            output=SmallOutput(),
            reserve_space_for_menu=0,
        )

        def after_render(app):
            screen = app.renderer._last_screen
            if screen is not None:
                rendered_lines.append(
                    [
                        "".join(
                            screen.data_buffer[y][x].char for x in range(10)
                        ).rstrip()
                        for y in range(3)
                    ]
                )
                app.exit(result="")

        session.app.after_render += after_render
        session.prompt()
        wrap = True
        session.prompt()

    assert rendered_lines == [
        ["abcdefghij", ">", ""],
        ["abcdefghij", "kl", ">"],
    ]
