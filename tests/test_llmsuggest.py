from __future__ import annotations

import re

import pytest

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document

try:
    from langchain_core.messages import AIMessage, BaseMessage

    from prompt_toolkit.contrib.auto_suggest import LLMSuggest
    module_loaded = True
except ModuleNotFoundError:
    module_loaded = False

     # LLM input              LLM output            Expected input + suggestion
test_data = [
    ("The quick brown",      " fox jumps over",    "The quick brown fox jumps over"),
    ("The quick brown ",     "fox jumps over",     "The quick brown fox jumps over"),
    ("The quick br",         "own fox jumps over", "The quick brown fox jumps over"),
    ("The quick br ",        "fox jumps over",     "The quick br fox jumps over"),
    ("The quick brown fox.", " he jumped over",    "The quick brown fox. He jumped over"),
    ("The quick brown fox",  "The quick brown fox jumps over", "The quick brown fox jumps over"),
    ("The quick brown fox,",  "jumped over",       "The quick brown fox, jumped over"),
    ("The quick brown fox'",  " s fence",          "The quick brown fox's fence"),
    ("The quick brown fox'",  "s fence",           "The quick brown fox's fence"),
]


class MockModel:
    def invoke(self, messages: list[dict[str, str]]) -> BaseMessage:
        # find the original text using a regex
        human_message = messages[1]["content"]
        if match := re.search(r"Original text: (.+)",human_message):
            original_text = match.group(1)
            for input, output, completion in test_data:
                if original_text == input:
                    return AIMessage(content=output)
        return AIMessage(content="")

@pytest.fixture
def chat_model():
    return MockModel()

@pytest.fixture
def suggester(chat_model) -> LLMSuggest:
    return LLMSuggest(chat_model, language="en_US")

@pytest.fixture
def buffer() -> Buffer:
    return Buffer()

@pytest.mark.parametrize(
    "input,output,expected_completion",
    test_data
)
@pytest.mark.skipif(not module_loaded, reason="The langchain, langchain_core and PyEnchant modules need to be installed to run these tests")
def test_suggest(suggester, buffer, input, output, expected_completion):
    document = Document(text=input)
    suggestion = suggester.get_suggestion(buffer, document)
    completion = input + suggestion.text
    assert completion == expected_completion
