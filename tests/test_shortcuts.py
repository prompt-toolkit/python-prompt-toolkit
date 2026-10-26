from __future__ import annotations

import asyncio

import pytest

from prompt_toolkit.filters import Condition
from prompt_toolkit.input.defaults import create_pipe_input
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


@pytest.mark.parametrize("show_frame", [True, Condition(lambda: True)])
def test_prompt_async_preserves_session_frame(show_frame):
    async def run():
        with create_pipe_input() as pipe_input:
            session = PromptSession(
                show_frame=show_frame, input=pipe_input, output=DummyOutput()
            )
            rendered_corners = []

            def after_render(app):
                screen = app.renderer.last_rendered_screen
                if screen is not None:
                    rendered_corners.append(screen.data_buffer[0][0].char)

            session.app.after_render += after_render
            pipe_input.send_text("hello\r")
            assert await session.prompt_async() == "hello"
            assert rendered_corners[0] == "┌"
            assert session.show_frame is show_frame

    asyncio.run(run())


def test_prompt_async_frame_override_persists():
    async def run():
        with create_pipe_input() as pipe_input:
            session = PromptSession(input=pipe_input, output=DummyOutput())
            rendered_corners = []

            def after_render(app):
                screen = app.renderer.last_rendered_screen
                if screen is not None:
                    rendered_corners.append(screen.data_buffer[0][0].char)

            session.app.after_render += after_render

            for kwargs, expected_frame in [
                ({"show_frame": True}, True),
                ({}, True),
                ({"show_frame": False}, False),
                ({}, False),
            ]:
                rendered_corners.clear()
                pipe_input.send_text("hello\r")
                assert await session.prompt_async(**kwargs) == "hello"
                assert (rendered_corners[0] == "┌") is expected_frame

    asyncio.run(run())
