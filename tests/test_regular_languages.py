from __future__ import annotations

import re

import pytest

from prompt_toolkit.completion import (
    CompleteEvent,
    Completer,
    Completion,
    WordCompleter,
)
from prompt_toolkit.contrib.regular_languages import compile
from prompt_toolkit.contrib.regular_languages.compiler import Match, Variables
from prompt_toolkit.contrib.regular_languages.completion import GrammarCompleter
from prompt_toolkit.contrib.regular_languages.validation import GrammarValidator
from prompt_toolkit.document import Document
from prompt_toolkit.validation import Validator


def test_simple_match():
    g = compile("hello|world")

    m = g.match("hello")
    assert isinstance(m, Match)

    m = g.match("world")
    assert isinstance(m, Match)

    m = g.match("somethingelse")
    assert m is None


def test_variable_varname():
    """
    Test `Variable` with varname.
    """
    g = compile("((?P<varname>hello|world)|test)")

    m = g.match("hello")
    variables = m.variables()
    assert isinstance(variables, Variables)
    assert variables.get("varname") == "hello"
    assert variables["varname"] == "hello"

    m = g.match("world")
    variables = m.variables()
    assert isinstance(variables, Variables)
    assert variables.get("varname") == "world"
    assert variables["varname"] == "world"

    m = g.match("test")
    variables = m.variables()
    assert isinstance(variables, Variables)
    assert variables.get("varname") is None
    assert variables["varname"] is None


def test_prefix():
    """
    Test `match_prefix`.
    """
    g = compile(r"(hello\ world|something\ else)")

    m = g.match_prefix("hello world")
    assert isinstance(m, Match)

    m = g.match_prefix("he")
    assert isinstance(m, Match)

    m = g.match_prefix("")
    assert isinstance(m, Match)

    m = g.match_prefix("som")
    assert isinstance(m, Match)

    m = g.match_prefix("hello wor")
    assert isinstance(m, Match)

    m = g.match_prefix("no-match")
    assert m.trailing_input().start == 0
    assert m.trailing_input().stop == len("no-match")

    m = g.match_prefix("hellotest")
    assert m.trailing_input().start == len("hello")
    assert m.trailing_input().stop == len("hellotest")


def test_completer():
    class completer1(Completer):
        def get_completions(self, document, complete_event):
            yield Completion(f"before-{document.text}-after", -len(document.text))
            yield Completion(f"before-{document.text}-after-B", -len(document.text))

    class completer2(Completer):
        def get_completions(self, document, complete_event):
            yield Completion(f"before2-{document.text}-after2", -len(document.text))
            yield Completion(f"before2-{document.text}-after2-B", -len(document.text))

    # Create grammar.  "var1" + "whitespace" + "var2"
    g = compile(r"(?P<var1>[a-z]*) \s+ (?P<var2>[a-z]*)")

    # Test 'get_completions()'
    completer = GrammarCompleter(g, {"var1": completer1(), "var2": completer2()})
    completions = list(
        completer.get_completions(Document("abc def", len("abc def")), CompleteEvent())
    )

    assert len(completions) == 2
    assert completions[0].text == "before2-def-after2"
    assert completions[0].start_position == -3
    assert completions[1].text == "before2-def-after2-B"
    assert completions[1].start_position == -3


def _escape_argument(text):
    return re.sub(r"([\\ ])", r"\\\1", text)


def _unescape_argument(text):
    return re.sub(r"\\(.)", r"\1", text)


@pytest.mark.parametrize("text", [r"foo\b", r"foo\ b", r"foo\\b", "foo b", "foo"])
@pytest.mark.parametrize("suffix", ["", " trailing"])
def test_completer_unescapes_once(text, suffix):
    grammar = compile(
        r"cmd\s+(?P<arg>.*)",
        escape_funcs={"arg": _escape_argument},
        unescape_funcs={"arg": _unescape_argument},
    )
    target = text + "ar"
    completer = GrammarCompleter(
        grammar, {"arg": WordCompleter([target], sentence=True)}
    )
    escaped = _escape_argument(text)
    before_cursor = "cmd " + escaped
    document = Document(before_cursor + suffix, len(before_cursor))

    completions = list(completer.get_completions(document, CompleteEvent()))

    assert len(completions) == 1
    assert completions[0].text == _escape_argument(target)
    assert completions[0].start_position == -len(escaped)


@pytest.mark.parametrize("text", [r"foo\b", r"foo\ b", r"foo\\b", "foo b", "foo"])
def test_validator_unescapes_once(text):
    received = []

    class RecordingValidator(Validator):
        def validate(self, document):
            received.append((document.text, document.cursor_position))

    grammar = compile(
        r"cmd\s+(?P<arg>.*)",
        unescape_funcs={"arg": _unescape_argument},
    )
    validator = GrammarValidator(grammar, {"arg": RecordingValidator()})
    validator.validate(Document("cmd " + _escape_argument(text)))

    assert received == [(text, len(text))]
