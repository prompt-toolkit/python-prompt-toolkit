from __future__ import annotations

import asyncio
import os
import re
import shutil
import tempfile
import threading
from contextlib import contextmanager

import pytest

from prompt_toolkit.completion import (
    CompleteEvent,
    Completer,
    Completion,
    DeduplicateCompleter,
    FuzzyWordCompleter,
    NestedCompleter,
    PathCompleter,
    ThreadedCompleter,
    WordCompleter,
    merge_completers,
)
from prompt_toolkit.document import Document
from prompt_toolkit.eventloop import aclosing


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


@pytest.fixture(params=["direct", "merged"])
def deduplicate_completer(request):
    def wrap(completer):
        if request.param == "direct":
            return DeduplicateCompleter(completer)
        return merge_completers([completer], deduplicate=True)

    return wrap


def test_deduplicate_completer_async(deduplicate_completer):
    document = Document("say ab after", cursor_position=6)
    event = CompleteEvent(completion_requested=True)
    first = Completion("abc", start_position=-2, display_meta="first")
    second = Completion("abcde", start_position=-2)
    completions = [
        Completion("ab", start_position=-2),  # No effect.
        first,
        Completion("c"),  # Same resulting text as the first completion.
        Completion(""),  # Another completion without an effect.
        second,
        Completion("abc", start_position=-2, display_meta="duplicate"),
    ]

    class AsyncCompleter(Completer):
        def get_completions(self, document, complete_event):
            return []

        async def get_completions_async(self, received_document, received_event):
            assert received_document is document
            assert received_event is event
            for completion in completions:
                yield completion

    completer = deduplicate_completer(AsyncCompleter())

    async def get_completions():
        return [c async for c in completer.get_completions_async(document, event)]

    async def run():
        # Each invocation has its own deduplication state, including concurrent ones.
        results = await asyncio.gather(get_completions(), get_completions())
        results.append(await get_completions())
        for result in results:
            assert len(result) == 2
            assert result[0] is first
            assert result[1] is second

    asyncio.run(run())


def test_deduplicate_completer_async_sync_fallback(deduplicate_completer):
    completer = deduplicate_completer(WordCompleter(["abc", "abc", "abcde", "ab"]))
    document = Document("ab")
    event = CompleteEvent()
    expected = list(completer.get_completions(document, event))
    assert [c.text for c in expected] == ["abc", "abcde"]

    async def run():
        assert [
            c async for c in completer.get_completions_async(document, event)
        ] == expected

    asyncio.run(run())


def test_deduplicate_completer_async_threaded(deduplicate_completer):
    threads = []

    class BlockingCompleter(Completer):
        def get_completions(self, document, complete_event):
            threads.append(threading.get_ident())
            yield Completion("abc")
            yield Completion("abc")
            yield Completion("abcde")

    completer = deduplicate_completer(ThreadedCompleter(BlockingCompleter()))

    async def run():
        assert [
            c.text
            async for c in completer.get_completions_async(
                Document(""), CompleteEvent()
            )
        ] == ["abc", "abcde"]
        assert len(threads) == 1
        assert threads[0] != threading.get_ident()

    asyncio.run(run())


def test_deduplicate_completer_async_closes_stream(deduplicate_completer):
    activity = []
    first = Completion("abc")

    class AsyncCompleter(Completer):
        def get_completions(self, document, complete_event):
            return []

        async def get_completions_async(self, document, complete_event):
            try:
                activity.append("first")
                yield first
                activity.append("second")
                yield Completion("abcde")
            finally:
                activity.append("closed")

    completer = deduplicate_completer(AsyncCompleter())

    async def run():
        async with aclosing(
            completer.get_completions_async(Document(""), CompleteEvent())
        ) as completions:
            assert await anext(completions) is first
            # Do not consume the rest of the stream to yield its first unique result.
            assert activity == ["first"]
        assert activity == ["first", "closed"]

    asyncio.run(run())


def test_deduplicate_completer_async_exception(deduplicate_completer):
    error = ValueError("completion failed")
    closed = []

    class AsyncCompleter(Completer):
        def get_completions(self, document, complete_event):
            return []

        async def get_completions_async(self, document, complete_event):
            try:
                yield Completion("abc")
                yield Completion("abc")
                raise error
            finally:
                closed.append(True)

    completer = deduplicate_completer(AsyncCompleter())

    async def run():
        results = []
        with pytest.raises(ValueError) as exc_info:
            async for completion in completer.get_completions_async(
                Document(""), CompleteEvent()
            ):
                results.append(completion.text)
        assert exc_info.value is error
        assert results == ["abc"]
        assert closed == [True]

    asyncio.run(run())


def test_deduplicate_completer_async_cancel(deduplicate_completer):
    closed = []

    async def run():
        started = asyncio.Event()

        class AsyncCompleter(Completer):
            def get_completions(self, document, complete_event):
                return []

            async def get_completions_async(self, document, complete_event):
                try:
                    started.set()
                    await asyncio.Future()
                    yield Completion("abc")
                finally:
                    closed.append(True)

        completer = deduplicate_completer(AsyncCompleter())
        completions = completer.get_completions_async(Document(""), CompleteEvent())
        task = asyncio.create_task(anext(completions))
        try:
            await asyncio.wait_for(started.wait(), timeout=1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert closed == [True]
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await completions.aclose()

    asyncio.run(run())


def test_merge_completers_async_deduplication_across_sources():
    class AsyncCompleter(Completer):
        def get_completions(self, document, complete_event):
            return []

        async def get_completions_async(self, document, complete_event):
            yield Completion("b", start_position=0)
            yield Completion("ac", start_position=-1, display_meta="async")

    completer = merge_completers(
        [WordCompleter(["ab"]), AsyncCompleter(), WordCompleter(["ac", "ad"])],
        deduplicate=True,
    )

    async def run():
        result = [
            (c.text, c.start_position, c.display_meta_text)
            async for c in completer.get_completions_async(
                Document("a"), CompleteEvent()
            )
        ]
        assert result == [("ab", -1, ""), ("ac", -1, "async"), ("ad", -1, "")]

    asyncio.run(run())


def test_deduplicate_completer_async_closes_threaded_producer(deduplicate_completer):
    closed = threading.Event()

    class BlockingCompleter(Completer):
        def get_completions(self, document, complete_event):
            try:
                for index in range(10000):
                    yield Completion(str(index))
            finally:
                closed.set()

    completer = deduplicate_completer(ThreadedCompleter(BlockingCompleter()))

    async def run():
        async with aclosing(
            completer.get_completions_async(Document(""), CompleteEvent())
        ) as completions:
            assert (await anext(completions)).text == "0"
        assert closed.is_set()

    asyncio.run(run())
