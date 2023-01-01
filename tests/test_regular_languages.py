from typing import Iterator

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.contrib.regular_languages import compile
from prompt_toolkit.contrib.regular_languages.compiler import Match, Variables
from prompt_toolkit.contrib.regular_languages.completion import GrammarCompleter
from prompt_toolkit.document import Document


def test_simple_match() -> None:
    g = compile("hello|world")

    m = g.match("hello")
    assert isinstance(m, Match)

    m = g.match("world")
    assert isinstance(m, Match)

    m = g.match("somethingelse")
    assert m is None


def test_variable_varname() -> None:
    """
    Test `Variable` with varname.
    """
    g = compile("((?P<varname>hello|world)|test)")

    m = g.match("hello")
    assert m is not None
    variables = m.variables()
    assert isinstance(variables, Variables)
    assert variables.get("varname") == "hello"
    assert variables["varname"] == "hello"

    m = g.match("world")
    assert m is not None
    variables = m.variables()
    assert isinstance(variables, Variables)
    assert variables.get("varname") == "world"
    assert variables["varname"] == "world"

    m = g.match("test")
    assert m is not None
    variables = m.variables()
    assert isinstance(variables, Variables)
    assert variables.get("varname") is None
    assert variables["varname"] is None


def test_prefix() -> None:
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
    assert m is not None
    match_variable = m.trailing_input()
    assert match_variable is not None
    assert match_variable.start == 0
    assert match_variable.stop == len("no-match")

    m = g.match_prefix("hellotest")
    assert m is not None
    match_variable = m.trailing_input()
    assert match_variable is not None
    assert match_variable.start == len("hello")
    assert match_variable.stop == len("hellotest")


def test_completer() -> None:
    class completer1(Completer):
        def get_completions(
            self, document: Document, complete_event: CompleteEvent
        ) -> Iterator[Completion]:
            yield Completion("before-%s-after" % document.text, -len(document.text))
            yield Completion("before-%s-after-B" % document.text, -len(document.text))

    class completer2(Completer):
        def get_completions(
            self, document: Document, complete_event: CompleteEvent
        ) -> Iterator[Completion]:
            yield Completion("before2-%s-after2" % document.text, -len(document.text))
            yield Completion("before2-%s-after2-B" % document.text, -len(document.text))

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
