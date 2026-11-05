# Key notation: \x1b is Escape, so "\x1bq" means Escape then lowercase q;
# "\x1bQ" means Escape then uppercase Q. Both stack the current input.
# Similarly, \r is Enter, \x03 is Ctrl-C, and \x04 is Ctrl-D.

from __future__ import annotations

import asyncio

import pytest

from prompt_toolkit.application import create_app_session
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import PromptSession, prompt
from prompt_toolkit.validation import Validator


@pytest.fixture
def session_and_input():
    with create_pipe_input() as inp:
        session = PromptSession(input=inp, output=DummyOutput())
        yield session, inp


@pytest.mark.parametrize("key", ["\x1bq", "\x1bQ"])
def test_push_input_and_restore_without_premature_history(session_and_input, key):
    session, inp = session_and_input
    inp.send_text("unfinished" + key + "command\r")
    assert session.prompt() == "command"
    assert session.history.get_strings() == ["command"]
    inp.send_text("\r")
    assert session.prompt() == "unfinished"
    assert session.history.get_strings() == ["command", "unfinished"]


def test_nested_input_stack_is_lifo_and_empty_push_is_ignored(session_and_input):
    session, inp = session_and_input
    inp.send_text("outer\x1bqinner\x1bQ\x1bQcommand\r")
    assert session.prompt() == "command"
    inp.send_text("\r")
    assert session.prompt() == "inner"
    inp.send_text("\r")
    assert session.prompt() == "outer"
    inp.send_text("\r")
    assert session.prompt() == ""


def test_multiline_document_preserves_cursor(session_and_input):
    session, inp = session_and_input
    document = Document("hello world\nnext", cursor_position=5)
    inp.send_text("\x1bQcommand\x1b\r")
    assert session.prompt(default=document, multiline=True) == "command"
    seen = []
    inp.send_text("!\x1b\r")
    result = session.prompt(
        pre_run=lambda: seen.append(session.default_buffer.document)
    )
    assert [(doc.text, doc.cursor_position) for doc in seen] == [
        ("hello world\nnext", 5)
    ]
    assert result == "hello! world\nnext"


@pytest.mark.parametrize(
    "default", ["explicit", Document("explicit", cursor_position=2)]
)
def test_nonempty_default_defers_pending_draft(session_and_input, default):
    session, inp = session_and_input
    inp.send_text("draft\x1bQcommand\r")
    assert session.prompt() == "command"
    inp.send_text("\r")
    assert session.prompt(default=default) == "explicit"
    inp.send_text("\r")
    assert session.prompt(default=Document()) == "draft"


@pytest.mark.parametrize(
    "key,exception", [("\x03", KeyboardInterrupt), ("\x04", EOFError)]
)
def test_cancel_or_blank_intervening_input_keeps_draft(
    session_and_input, key, exception
):
    session, inp = session_and_input
    inp.send_text("draft\x1bQ" + key)
    with pytest.raises(exception):
        session.prompt()
    inp.send_text(" \r")
    assert session.prompt() == " "
    inp.send_text("command\r")
    assert session.prompt() == "command"
    inp.send_text("\r")
    assert session.prompt() == "draft"


def test_explicit_default_interrupt_keeps_ready_draft(session_and_input):
    session, inp = session_and_input
    inp.send_text("draft\x1bQcommand\r")
    assert session.prompt() == "command"
    inp.send_text("\x03")
    with pytest.raises(KeyboardInterrupt):
        session.prompt(default="explicit")
    inp.send_text("\r")
    assert session.prompt() == "draft"


def test_failed_validation_does_not_make_draft_ready(session_and_input):
    session, inp = session_and_input
    validator = Validator.from_callable(
        lambda text: text in ("draft", "ok"), error_message="Use ok"
    )
    # Rejected Enter followed by interrupt must leave the draft pending.
    inp.send_text("draft\x1bQbad\r\x03")
    with pytest.raises(KeyboardInterrupt):
        session.prompt(validator=validator)
    inp.send_text("\x04")
    with pytest.raises(EOFError):
        session.prompt()
    inp.send_text("ok\r")
    assert session.prompt() == "ok"
    inp.send_text("\r")
    assert session.prompt() == "draft"
    assert "bad" not in session.history.get_strings()


def test_disabling_and_reenabling_preserves_pending_draft(session_and_input):
    session, inp = session_and_input
    inp.send_text("draft\x1bQcommand\r")
    assert session.prompt() == "command"
    inp.send_text("disabled\r")
    assert session.prompt(enable_input_stack=False) == "disabled"
    inp.send_text("still disabled\r")
    assert session.prompt() == "still disabled"
    inp.send_text("\r")
    assert session.prompt(enable_input_stack=True) == "draft"


@pytest.mark.parametrize("key", ["\x1bq", "\x1bQ"])
def test_explicit_opt_out_matches_one_shot_helper(key):
    with create_pipe_input() as inp:
        session = PromptSession(
            input=inp, output=DummyOutput(), enable_input_stack=False
        )
        inp.send_text("draft" + key + "command\r")
        disabled_result = session.prompt()
        inp.send_text("\r")
        assert session.prompt() == ""
    with create_pipe_input() as inp:
        with create_app_session(input=inp, output=DummyOutput()):
            inp.send_text("draft" + key + "command\r")
            assert prompt() == disabled_result
    assert disabled_result != "command"


def test_sessions_do_not_share_stacked_input(session_and_input):
    session, inp = session_and_input
    inp.send_text("draft\x1bQcommand\r")
    assert session.prompt() == "command"
    with create_pipe_input() as other_input:
        other_session = PromptSession(
            input=other_input, output=DummyOutput(), enable_input_stack=True
        )
        other_input.send_text("\r")
        assert other_session.prompt() == ""
    inp.send_text("\r")
    assert session.prompt() == "draft"


def test_history_search_stays_in_its_buffer(session_and_input):
    session, inp = session_and_input
    session.history.append_string("history match")
    inp.send_text("draft\x1bQ\x12history\r\r")
    assert session.prompt() == "history match"
    inp.send_text("\r")
    assert session.prompt() == "draft"


def test_accept_default_can_accept_a_restored_draft(session_and_input):
    session, inp = session_and_input
    inp.send_text("draft\x1bQcommand\r")
    assert session.prompt() == "command"
    assert session.prompt(accept_default=True) == "draft"


def test_input_stack_with_in_thread(session_and_input):
    session, inp = session_and_input
    inp.send_text("draft\x1bQcommand\r")
    assert session.prompt(in_thread=True) == "command"
    inp.send_text("\r")
    assert session.prompt(in_thread=True) == "draft"


def test_async_prompt_stacks_and_restores_documents(session_and_input):
    session, inp = session_and_input

    async def run():
        inp.send_text("\x1bQcommand\r")
        assert (
            await session.prompt_async(default=Document("draft", cursor_position=2))
            == "command"
        )
        inp.send_text("!\r")
        assert await session.prompt_async() == "dr!aft"
        inp.send_text("outer\x1bqinner\x1bQcommand\r")
        assert await session.prompt_async() == "command"
        assert (
            await session.prompt_async(default="explicit", accept_default=True)
            == "explicit"
        )
        assert await session.prompt_async(accept_default=True) == "inner"
        assert await session.prompt_async(accept_default=True) == "outer"
        inp.send_text("draft\x1bQcommand\r")
        assert await session.prompt_async(enable_input_stack=False) != "command"
        inp.send_text("new draft\x1bQcommand\r")
        assert await session.prompt_async(enable_input_stack=True) == "command"
        assert await session.prompt_async(accept_default=True) == "new draft"

    asyncio.run(run())


def test_async_cancellation_keeps_unfinished_stack(session_and_input):
    session, inp = session_and_input

    async def run():
        pushed = asyncio.Event()

        def changed(buffer):
            if not buffer.text and session._input_stack:
                pushed.set()

        session.default_buffer.on_text_changed += changed
        inp.send_text("draft\x1bQ")
        task = asyncio.create_task(session.prompt_async())
        await asyncio.wait_for(pushed.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        inp.send_text("command\r")
        assert await session.prompt_async() == "command"
        inp.send_text("\r")
        assert await session.prompt_async() == "draft"

    asyncio.run(run())


@pytest.mark.parametrize("selection", ["\x1b[A", "\x12old\r"])
def test_push_recalled_entry_preserves_history_and_starts_at_newest(selection):
    with create_pipe_input() as inp:
        session = PromptSession(
            input=inp,
            output=DummyOutput(),
            history=InMemoryHistory(["old history", "new history"]),
            enable_input_stack=True,
        )
        # Recall the older entry, stack it, then navigate from a fresh input slot.
        inp.send_text("\x1b[A\x1b[A\x1bQ" + selection + "\r")
        expected = "new history" if selection == "\x1b[A" else "old history"
        assert session.prompt() == expected
        inp.send_text("\r")
        assert session.prompt() == "old history"
