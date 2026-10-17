from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from importlib import import_module
from unittest.mock import AsyncMock, Mock

import pytest

from prompt_toolkit.application import Application
from prompt_toolkit.completion import Completion
from prompt_toolkit.data_structures import Size
from prompt_toolkit.formatted_text import fragment_list_to_text
from prompt_toolkit.input import DummyInput
from prompt_toolkit.key_binding.bindings import completion
from prompt_toolkit.output import DummyOutput


@pytest.mark.parametrize("rows, page_count", [(1, 3), (2, 3), (24, 1)])
def test_readline_completion_pagination_in_short_terminal(
    monkeypatch, rows, page_count
):
    class Output(DummyOutput):
        def get_size(self):
            return Size(rows=rows, columns=12)

    @asynccontextmanager
    async def in_terminal(**kwargs):
        yield

    confirm = AsyncMock(return_value=True)
    more = AsyncMock(return_value=True)
    monkeypatch.setattr(completion, "in_terminal", in_terminal)
    monkeypatch.setattr(
        import_module("prompt_toolkit.shortcuts.prompt"),
        "create_confirm_session",
        Mock(return_value=Mock(prompt_async=confirm)),
    )
    monkeypatch.setattr(
        completion, "_create_more_session", Mock(return_value=Mock(prompt_async=more))
    )
    app = Application(input=DummyInput(), output=Output())
    printed = Mock()
    monkeypatch.setattr(app, "print_text", printed)
    words = ["alpha", "bravo", "delta", "gamma", "omega", "sigma"]

    async def run():
        await completion._display_completions_like_readline(
            app, [Completion(word) for word in words]
        )

    asyncio.run(run())

    assert printed.call_count == page_count
    assert confirm.await_count == (1 if page_count > 1 else 0)
    assert more.await_count == page_count - 1
    output = "".join(
        fragment_list_to_text(call.args[0]) for call in printed.call_args_list
    )
    assert sorted(output.split()) == sorted(words)
