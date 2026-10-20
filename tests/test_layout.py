from __future__ import annotations

from asyncio import run

import pytest

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout import InvalidLayoutError, Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.lexers import DynamicLexer, Lexer, SimpleLexer


def test_layout_class():
    c1 = BufferControl()
    c2 = BufferControl()
    c3 = BufferControl()
    win1 = Window(content=c1)
    win2 = Window(content=c2)
    win3 = Window(content=c3)

    layout = Layout(container=VSplit([HSplit([win1, win2]), win3]))

    # Listing of windows/controls.
    assert list(layout.find_all_windows()) == [win1, win2, win3]
    assert list(layout.find_all_controls()) == [c1, c2, c3]

    # Focusing something.
    layout.focus(c1)
    assert layout.has_focus(c1)
    assert layout.has_focus(win1)
    assert layout.current_control == c1
    assert layout.previous_control == c1

    layout.focus(c2)
    assert layout.has_focus(c2)
    assert layout.has_focus(win2)
    assert layout.current_control == c2
    assert layout.previous_control == c1

    layout.focus(win3)
    assert layout.has_focus(c3)
    assert layout.has_focus(win3)
    assert layout.current_control == c3
    assert layout.previous_control == c2

    # Pop focus. This should focus the previous control again.
    layout.focus_last()
    assert layout.has_focus(c2)
    assert layout.has_focus(win2)
    assert layout.current_control == c2
    assert layout.previous_control == c1


def test_create_invalid_layout():
    with pytest.raises(InvalidLayoutError):
        Layout(HSplit([]))


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_nested_dynamic_lexer_invalidation(depth):
    async def check():
        current = None
        lexer = DynamicLexer(lambda: current)
        for _ in range(depth - 1):
            inner = lexer
            lexer = DynamicLexer(lambda inner=inner: inner)

        control = BufferControl(buffer=Buffer(document=Document("text")), lexer=lexer)
        for style in [None, "class:first", "class:second", None]:
            current = SimpleLexer(style) if style is not None else None
            fragments = control.create_content(80, 24).get_line(0)
            assert fragments == [(style or "", "text"), ("", " ")]

    run(check())


def test_dynamic_lexer_preserves_custom_invalidation():
    class ChangingLexer(Lexer):
        style = "class:first"
        calls = 0

        def lex_document(self, document):
            self.calls += 1
            style = self.style
            return lambda lineno: [(style, document.lines[lineno])]

        def invalidation_hash(self):
            return self.style

    async def check():
        inner = ChangingLexer()
        lexer = DynamicLexer(lambda: inner)
        control = BufferControl(buffer=Buffer(document=Document("text")), lexer=lexer)

        for style, expected_calls in [
            ("class:first", 1),
            ("class:first", 1),
            ("class:second", 2),
            ("class:second", 2),
            ("class:first", 2),
        ]:
            inner.style = style
            fragments = control.create_content(80, 24).get_line(0)
            assert fragments == [(style, "text"), ("", " ")]
            assert inner.calls == expected_calls

    run(check())


def test_dynamic_lexer_invalidates_when_identity_changes():
    class RevisionLexer(SimpleLexer):
        def invalidation_hash(self):
            return 0

    async def check():
        current = RevisionLexer("class:first")
        lexer = DynamicLexer(lambda: current)
        control = BufferControl(buffer=Buffer(document=Document("text")), lexer=lexer)
        assert control.create_content(80, 24).get_line(0) == [
            ("class:first", "text"),
            ("", " "),
        ]

        current = RevisionLexer("class:second")
        assert control.create_content(80, 24).get_line(0) == [
            ("class:second", "text"),
            ("", " "),
        ]

    run(check())
