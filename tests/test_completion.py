from __future__ import annotations

import os
import re
import shutil
import tempfile
from contextlib import contextmanager

import pytest

from prompt_toolkit.completion import (
    CompleteEvent,
    FuzzyWordCompleter,
    NestedCompleter,
    PathCompleter,
    WordCompleter,
    merge_completers,
)
from prompt_toolkit.document import Document


@contextmanager
def chdir(directory):
    """Context manager for current working directory temporary change."""
    orig_dir = os.getcwd()
    os.chdir(directory)

    try:
        yield
    finally:
        os.chdir(orig_dir)


def write_test_files(test_dir, names=None):
    """Write test files in test_dir using the names list."""
    names = names or range(10)
    for i in names:
        with open(os.path.join(test_dir, str(i)), "wb") as out:
            out.write(b"")


def test_pathcompleter_completes_in_current_directory():
    completer = PathCompleter()
    doc_text = ""
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completions = list(completer.get_completions(doc, event))
    assert len(completions) > 0


def test_pathcompleter_completes_files_in_current_directory():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    expected = sorted(str(i) for i in range(10))

    if not test_dir.endswith(os.path.sep):
        test_dir += os.path.sep

    with chdir(test_dir):
        completer = PathCompleter()
        # this should complete on the cwd
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = sorted(c.text for c in completions)
        assert expected == result

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_completes_files_in_absolute_directory():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    expected = sorted(str(i) for i in range(10))

    test_dir = os.path.abspath(test_dir)
    if not test_dir.endswith(os.path.sep):
        test_dir += os.path.sep

    completer = PathCompleter()
    # force unicode
    doc_text = str(test_dir)
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completions = list(completer.get_completions(doc, event))
    result = sorted(c.text for c in completions)
    assert expected == result

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_completes_directories_with_only_directories():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # create a sub directory there
    os.mkdir(os.path.join(test_dir, "subdir"))

    if not test_dir.endswith(os.path.sep):
        test_dir += os.path.sep

    with chdir(test_dir):
        completer = PathCompleter(only_directories=True)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert ["subdir"] == result

    # check that there is no completion when passing a file
    with chdir(test_dir):
        completer = PathCompleter(only_directories=True)
        doc_text = "1"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        assert [] == completions

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_respects_completions_under_min_input_len():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # min len:1 and no text
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=1)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        assert [] == completions

    # min len:1 and text of len 1
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=1)
        doc_text = "1"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert [""] == result

    # min len:0 and text of len 2
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=0)
        doc_text = "1"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert [""] == result

    # create 10 files with a 2 char long name
    for i in range(10):
        with open(os.path.join(test_dir, str(i) * 2), "wb") as out:
            out.write(b"")

    # min len:1 and text of len 1
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=1)
        doc_text = "2"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = sorted(c.text for c in completions)
        assert ["", "2"] == result

    # min len:2 and text of len 1
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=2)
        doc_text = "2"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        assert [] == completions

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_does_not_expanduser_by_default():
    completer = PathCompleter()
    doc_text = "~"
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completions = list(completer.get_completions(doc, event))
    assert [] == completions


def test_pathcompleter_can_expanduser():
    completer = PathCompleter(expanduser=True)
    doc_text = "~"
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completions = list(completer.get_completions(doc, event))
    assert len(completions) > 0


def test_pathcompleter_can_apply_file_filter():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # add a .csv file
    with open(os.path.join(test_dir, "my.csv"), "wb") as out:
        out.write(b"")

    file_filter = lambda f: f and f.endswith(".csv")

    with chdir(test_dir):
        completer = PathCompleter(file_filter=file_filter)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert ["my.csv"] == result

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_get_paths_constrains_path():
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # add a subdir with 10 other files with different names
    subdir = os.path.join(test_dir, "subdir")
    os.mkdir(subdir)
    write_test_files(subdir, "abcdefghij")

    get_paths = lambda: ["subdir"]

    with chdir(test_dir):
        completer = PathCompleter(get_paths=get_paths)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        expected = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        assert expected == result

    # cleanup
    shutil.rmtree(test_dir)


def test_word_completer_static_word_list():
    completer = WordCompleter(["abc", "def", "aaa"])

    # Static list on empty input.
    completions = completer.get_completions(Document(""), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "def", "aaa"]

    # Static list on non-empty input.
    completions = completer.get_completions(Document("a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]

    completions = completer.get_completions(Document("A"), CompleteEvent())
    assert [c.text for c in completions] == []

    # Multiple words ending with space. (Accept all options)
    completions = completer.get_completions(Document("test "), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "def", "aaa"]

    # Multiple words. (Check last only.)
    completions = completer.get_completions(Document("test a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]


def test_word_completer_ignore_case():
    completer = WordCompleter(["abc", "def", "aaa"], ignore_case=True)
    completions = completer.get_completions(Document("a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]

    completions = completer.get_completions(Document("A"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]


def test_word_completer_match_middle():
    completer = WordCompleter(["abc", "def", "abca"], match_middle=True)
    completions = completer.get_completions(Document("bc"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "abca"]


def test_word_completer_sentence():
    # With sentence=True
    completer = WordCompleter(
        ["hello world", "www", "hello www", "hello there"], sentence=True
    )
    completions = completer.get_completions(Document("hello w"), CompleteEvent())
    assert [c.text for c in completions] == ["hello world", "hello www"]

    # With sentence=False
    completer = WordCompleter(
        ["hello world", "www", "hello www", "hello there"], sentence=False
    )
    completions = completer.get_completions(Document("hello w"), CompleteEvent())
    assert [c.text for c in completions] == ["www"]


def test_word_completer_dynamic_word_list():
    called = [0]

    def get_words():
        called[0] += 1
        return ["abc", "def", "aaa"]

    completer = WordCompleter(get_words)

    # Dynamic list on empty input.
    completions = completer.get_completions(Document(""), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "def", "aaa"]
    assert called[0] == 1

    # Static list on non-empty input.
    completions = completer.get_completions(Document("a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]
    assert called[0] == 2


def test_word_completer_pattern():
    # With a pattern which support '.'
    completer = WordCompleter(
        ["abc", "a.b.c", "a.b", "xyz"],
        pattern=re.compile(r"^([a-zA-Z0-9_.]+|[^a-zA-Z0-9_.\s]+)"),
    )
    completions = completer.get_completions(Document("a."), CompleteEvent())
    assert [c.text for c in completions] == ["a.b.c", "a.b"]

    # Without pattern
    completer = WordCompleter(["abc", "a.b.c", "a.b", "xyz"])
    completions = completer.get_completions(Document("a."), CompleteEvent())
    assert [c.text for c in completions] == []


def test_fuzzy_completer():
    collection = [
        "migrations.py",
        "django_migrations.py",
        "django_admin_log.py",
        "api_user.doc",
        "user_group.doc",
        "users.txt",
        "accounts.txt",
        "123.py",
        "test123test.py",
    ]
    completer = FuzzyWordCompleter(collection)
    completions = completer.get_completions(Document("txt"), CompleteEvent())
    assert [c.text for c in completions] == ["users.txt", "accounts.txt"]

    completions = completer.get_completions(Document("djmi"), CompleteEvent())
    assert [c.text for c in completions] == [
        "django_migrations.py",
        "django_admin_log.py",
    ]

    completions = completer.get_completions(Document("mi"), CompleteEvent())
    assert [c.text for c in completions] == [
        "migrations.py",
        "django_migrations.py",
        "django_admin_log.py",
    ]

    completions = completer.get_completions(Document("user"), CompleteEvent())
    assert [c.text for c in completions] == [
        "user_group.doc",
        "users.txt",
        "api_user.doc",
    ]

    completions = completer.get_completions(Document("123"), CompleteEvent())
    assert [c.text for c in completions] == ["123.py", "test123test.py"]

    completions = completer.get_completions(Document("miGr"), CompleteEvent())
    assert [c.text for c in completions] == [
        "migrations.py",
        "django_migrations.py",
    ]

    # Multiple words ending with space. (Accept all options)
    completions = completer.get_completions(Document("test "), CompleteEvent())
    assert [c.text for c in completions] == collection

    # Multiple words. (Check last only.)
    completions = completer.get_completions(Document("test txt"), CompleteEvent())
    assert [c.text for c in completions] == ["users.txt", "accounts.txt"]


def test_nested_completer():
    completer = NestedCompleter.from_nested_dict(
        {
            "show": {
                "version": None,
                "clock": None,
                "interfaces": None,
                "ip": {"interface": {"brief"}},
            },
            "exit": None,
        }
    )

    # Empty input.
    completions = completer.get_completions(Document(""), CompleteEvent())
    assert {c.text for c in completions} == {"show", "exit"}

    # One character.
    completions = completer.get_completions(Document("s"), CompleteEvent())
    assert {c.text for c in completions} == {"show"}

    # One word.
    completions = completer.get_completions(Document("show"), CompleteEvent())
    assert {c.text for c in completions} == {"show"}

    # One word + space.
    completions = completer.get_completions(Document("show "), CompleteEvent())
    assert {c.text for c in completions} == {"version", "clock", "interfaces", "ip"}

    # One word + space + one character.
    completions = completer.get_completions(Document("show i"), CompleteEvent())
    assert {c.text for c in completions} == {"ip", "interfaces"}

    # One space + one word + space + one character.
    completions = completer.get_completions(Document(" show i"), CompleteEvent())
    assert {c.text for c in completions} == {"ip", "interfaces"}

    # Test nested set.
    completions = completer.get_completions(
        Document("show ip interface br"), CompleteEvent()
    )
    assert {c.text for c in completions} == {"brief"}


@pytest.mark.parametrize(
    "command, text, start_position",
    [
        ("show", "SHOW ", 0),
        ("SHOW", "show v", -1),
        ("ShOw", "sHoW v", -1),
        ("show", "  SHOW   v", -1),
        ("\u0130", "i\u0307 v", -1),
        ("i\u0307", "\u0130 v", -1),
    ],
)
def test_nested_completer_ignore_case(command, text, start_position):
    completer = NestedCompleter.from_nested_dict({command: {"version": None}})

    completions = list(completer.get_completions(Document(text), CompleteEvent()))
    assert [(c.text, c.start_position) for c in completions] == [
        ("version", start_position)
    ]


def test_nested_completer_ignore_case_multiple_levels():
    completer = NestedCompleter.from_nested_dict(
        {"Show": {"IP": {"Interface": {"brief"}}}}
    )

    completions = completer.get_completions(
        Document("SHOW ip INTERFACE b"), CompleteEvent()
    )
    assert [(c.text, c.start_position) for c in completions] == [("brief", -1)]


@pytest.mark.parametrize("ignore_case", [False, True])
@pytest.mark.parametrize("command", ["show", "SHOW"])
def test_nested_completer_prefers_exact_match(ignore_case, command):
    completer = NestedCompleter(
        {"show": WordCompleter(["version"]), "SHOW": None},
        ignore_case=ignore_case,
    )

    completions = completer.get_completions(Document(command + " "), CompleteEvent())
    assert [c.text for c in completions] == (["version"] if command == "show" else [])


def test_nested_completer_case_sensitive():
    completer = NestedCompleter({"show": WordCompleter(["version"])}, ignore_case=False)

    completions = completer.get_completions(Document("SHOW "), CompleteEvent())
    assert list(completions) == []


@pytest.mark.parametrize("terminal", [False, True])
def test_nested_completer_case_insensitive_collision(terminal):
    completer = NestedCompleter(
        {
            "Show": None if terminal else WordCompleter(["version"]),
            "SHOW": WordCompleter(["clock"]),
        }
    )

    completions = completer.get_completions(Document("show "), CompleteEvent())
    assert [c.text for c in completions] == ([] if terminal else ["version"])


def test_nested_completer_preserves_child_case_sensitivity():
    completer = NestedCompleter({"show": WordCompleter(["version"], ignore_case=False)})

    completions = completer.get_completions(Document("SHOW V"), CompleteEvent())
    assert list(completions) == []


def test_nested_completer_ignore_case_before_cursor():
    completer = NestedCompleter.from_nested_dict({"show": {"version": None}})
    document = Document("SHOW v suffix", cursor_position=6)

    completions = completer.get_completions(document, CompleteEvent())
    assert [(c.text, c.start_position) for c in completions] == [("version", -1)]


def test_nested_completer_case_insensitive_options_update():
    options = {"show": WordCompleter(["version"])}
    completer = NestedCompleter(options)
    options["show"] = WordCompleter(["clock"])

    completions = completer.get_completions(Document("SHOW "), CompleteEvent())
    assert [c.text for c in completions] == ["clock"]


def test_deduplicate_completer():
    def create_completer(deduplicate: bool):
        return merge_completers(
            [
                WordCompleter(["hello", "world", "abc", "def"]),
                WordCompleter(["xyz", "xyz", "abc", "def"]),
            ],
            deduplicate=deduplicate,
        )

    completions = list(
        create_completer(deduplicate=False).get_completions(
            Document(""), CompleteEvent()
        )
    )
    assert len(completions) == 8

    completions = list(
        create_completer(deduplicate=True).get_completions(
            Document(""), CompleteEvent()
        )
    )
    assert len(completions) == 5
