from __future__ import annotations

from asyncio import run
from threading import get_ident
from unittest.mock import Mock

import pytest

from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.validation import (
    ConditionalValidator,
    ThreadedValidator,
    ValidationError,
    Validator,
)


def test_conditional_validator_async():
    validator = Mock(spec=Validator)
    enabled = False
    conditional = ConditionalValidator(validator, Condition(lambda: enabled))
    document = Document("input")

    async def validate():
        nonlocal enabled
        await conditional.validate_async(document)
        validator.validate_async.assert_not_called()

        enabled = True
        await conditional.validate_async(document)
        validator.validate_async.assert_awaited_once_with(document)
        validator.validate.assert_not_called()

        enabled = False
        await conditional.validate_async(document)
        validator.validate_async.assert_awaited_once_with(document)

    run(validate())


def test_conditional_validator_async_error():
    validator = Mock(spec=Validator)
    error = ValidationError(cursor_position=2, message="Invalid input")
    validator.validate_async.side_effect = error
    conditional = ConditionalValidator(validator, True)

    with pytest.raises(ValidationError) as exc_info:
        run(conditional.validate_async(Document("input")))

    assert exc_info.value is error
    validator.validate.assert_not_called()


def test_conditional_threaded_validator():
    thread_ids = []
    validator = Validator.from_callable(
        lambda text: thread_ids.append(get_ident()) is None
    )
    conditional = ConditionalValidator(ThreadedValidator(validator), True)
    document = Document("input")

    conditional.validate(document)
    run(conditional.validate_async(document))

    assert len(thread_ids) == 2
    assert thread_ids[0] == get_ident()
    assert thread_ids[1] != get_ident()


@pytest.mark.parametrize("enabled", [False, True])
def test_conditional_sync_validator_async(enabled):
    calls = []
    validator = Validator.from_callable(lambda text: calls.append(text) is None)
    conditional = ConditionalValidator(validator, enabled)

    run(conditional.validate_async(Document("input")))

    assert calls == (["input"] if enabled else [])
