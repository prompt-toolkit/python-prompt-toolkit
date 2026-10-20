from __future__ import annotations

from asyncio import run
from threading import get_ident
from unittest.mock import Mock

import pytest

from prompt_toolkit.auto_suggest import (
    AutoSuggest,
    ConditionalAutoSuggest,
    Suggestion,
    ThreadedAutoSuggest,
)
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition


def test_conditional_auto_suggest_async():
    auto_suggest = Mock(spec=AutoSuggest)
    suggestion = Suggestion("completion")
    auto_suggest.get_suggestion_async.return_value = suggestion
    enabled = False
    conditional = ConditionalAutoSuggest(auto_suggest, Condition(lambda: enabled))
    buffer = Buffer()
    document = Document("input")

    async def suggest():
        nonlocal enabled
        assert await conditional.get_suggestion_async(buffer, document) is None
        auto_suggest.get_suggestion_async.assert_not_called()

        enabled = True
        assert await conditional.get_suggestion_async(buffer, document) is suggestion
        auto_suggest.get_suggestion_async.assert_awaited_once_with(buffer, document)
        auto_suggest.get_suggestion.assert_not_called()

        enabled = False
        assert await conditional.get_suggestion_async(buffer, document) is None
        auto_suggest.get_suggestion_async.assert_awaited_once_with(buffer, document)

    run(suggest())


def test_conditional_auto_suggest_async_error():
    auto_suggest = Mock(spec=AutoSuggest)
    error = RuntimeError("Suggestion failed")
    auto_suggest.get_suggestion_async.side_effect = error
    conditional = ConditionalAutoSuggest(auto_suggest, True)

    with pytest.raises(RuntimeError) as exc_info:
        run(conditional.get_suggestion_async(Buffer(), Document("input")))

    assert exc_info.value is error
    auto_suggest.get_suggestion.assert_not_called()


def test_conditional_threaded_auto_suggest():
    thread_ids = []
    suggestion = Suggestion("completion")

    class TestAutoSuggest(AutoSuggest):
        def get_suggestion(self, buffer, document):
            thread_ids.append(get_ident())
            return suggestion

    conditional = ConditionalAutoSuggest(ThreadedAutoSuggest(TestAutoSuggest()), True)
    buffer = Buffer()
    document = Document("input")

    assert conditional.get_suggestion(buffer, document) is suggestion
    assert run(conditional.get_suggestion_async(buffer, document)) is suggestion
    assert len(thread_ids) == 2
    assert thread_ids[0] == get_ident()
    assert thread_ids[1] != get_ident()


@pytest.mark.parametrize("enabled", [False, True])
def test_conditional_sync_auto_suggest_async(enabled):
    calls = []
    suggestion = Suggestion("completion")

    class TestAutoSuggest(AutoSuggest):
        def get_suggestion(self, buffer, document):
            calls.append((buffer, document))
            return suggestion

    conditional = ConditionalAutoSuggest(TestAutoSuggest(), enabled)
    buffer = Buffer()
    document = Document("input")

    result = run(conditional.get_suggestion_async(buffer, document))

    assert result is (suggestion if enabled else None)
    assert calls == ([(buffer, document)] if enabled else [])
