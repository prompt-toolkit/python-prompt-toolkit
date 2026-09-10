from __future__ import annotations

import asyncio

import pytest

from prompt_toolkit.application import Application, create_app_session
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import HTML, fragment_list_to_text, to_formatted_text
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import choice, choice_input
from prompt_toolkit.shortcuts.choice_input import ChoiceInput
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import CheckboxList

OPTIONS = [("a", "Alpha"), ("b", "Bravo"), ("c", "Charlie")]


@pytest.fixture
def mock_input():
    with create_pipe_input() as pipe_input:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            yield pipe_input


@pytest.fixture(params=["choice", "prompt", "prompt_async"])
def run_choice(request, mock_input):
    """Exercise the convenience, reusable, and asynchronous entry points."""

    def run(keys, *, options=OPTIONS, **kwargs):
        mock_input.send_text(keys)
        if request.param == "choice":
            return choice("Choose:", options=options, **kwargs)

        prompt_kwargs = {
            name: kwargs.pop(name)
            for name in ("multiple_selection", "default_values")
            if name in kwargs
        }
        selection = ChoiceInput(message="Choose:", options=options, **kwargs)
        if request.param == "prompt":
            return selection.prompt(**prompt_kwargs)
        return asyncio.run(
            asyncio.wait_for(
                selection.prompt_async(**prompt_kwargs),
                timeout=2,
            )
        )

    return run


@pytest.mark.parametrize(
    "keys, expected",
    [
        ("\r", []),
        (" \r", ["a"]),
        ("  \r", []),
        (" \x1b[B \r", ["a", "b"]),
        ("3 1 \r", ["a", "c"]),
        ("2 2 \r", []),
        ("\x1b[B\r", []),
        ("j \x1b[B \x1b[A \r", ["c"]),
        ("k \r", ["a"]),
        ("9 \r", ["c"]),
        ("c \r", ["c"]),
        ("C \r", ["c"]),
        ("3 1 2 1 \r", ["b", "c"]),
    ],
)
def test_multiple_selection(run_choice, keys, expected):
    assert run_choice(keys, multiple_selection=True) == expected


@pytest.mark.parametrize(
    "keys, expected",
    [
        ("\r", "a"),
        ("\x1b[B\r", "b"),
        ("3\r", "c"),
        ("2\r", "b"),
        (" \r", "a"),
        ("j\r", "b"),
        ("jk\r", "a"),
    ],
)
def test_single_selection_unchanged(run_choice, keys, expected):
    assert run_choice(keys) == expected


@pytest.mark.parametrize(
    "kwargs, keys, expected",
    [
        ({"default": "b"}, "\r", ["b"]),
        ({"default": "missing"}, "\r", []),
        ({"default_values": ["c", "a"]}, "\r", ["a", "c"]),
        ({"default_values": ["b", "b"]}, " \r", []),
        ({"default_values": ["missing", "b"]}, "\r", ["b"]),
        ({"default_values": ["missing"]}, "\r", []),
        ({"default": "c", "default_values": []}, "\r", []),
        ({"default": "c", "default_values": ["a"]}, "\r", ["a"]),
        ({"default_values": ("c", "b")}, " \r", ["b"]),
    ],
)
def test_multiple_defaults(run_choice, kwargs, keys, expected):
    assert run_choice(keys, multiple_selection=True, **kwargs) == expected


def test_defaults_are_not_mutated(run_choice):
    defaults = ["c", "a", "a", "missing"]
    result = run_choice(" \r", multiple_selection=True, default_values=defaults)
    assert result == ["a"]
    assert defaults == ["c", "a", "a", "missing"]
    assert result is not defaults


def test_unhashable_values(run_choice):
    first = {"id": 1}
    second = {"id": 2}
    result = run_choice(
        "2 1 \r",
        options=[(first, "First"), (second, "Second")],
        multiple_selection=True,
    )
    assert result == [first, second]
    assert result[0] is first
    assert result[1] is second


def test_duplicate_unhashable_defaults_toggle_once(run_choice):
    assert (
        run_choice(
            " \r",
            options=[([1], "First"), ([2], "Second")],
            multiple_selection=True,
            default_values=[[1], [1]],
        )
        == []
    )


def test_falsey_values(run_choice):
    assert run_choice(
        "4 3 2 1 \r",
        options=[(0, "Zero"), ("", "Empty"), (None, "None"), ([], "List")],
        multiple_selection=True,
    ) == [0, "", None, []]


@pytest.mark.parametrize("default", [0, ""])
def test_falsey_single_default_in_multiple_mode(run_choice, default):
    assert run_choice(
        "\r", options=[(default, "Value")], default=default, multiple_selection=True
    ) == [default]


def test_none_can_be_checked_by_default_values(run_choice):
    assert run_choice(
        "\r", options=[(None, "None")], default_values=[None], multiple_selection=True
    ) == [None]


@pytest.mark.parametrize("keys, expected", [(" \r", ["a"]), ("1 2 \r", [])])
def test_duplicate_option_values(run_choice, keys, expected):
    assert (
        run_choice(
            keys,
            options=[("a", "First"), ("a", "Same value"), ("b", "Other")],
            multiple_selection=True,
        )
        == expected
    )


def test_single_list_value_is_not_wrapped(run_choice):
    value = [1, 2]
    assert run_choice("\r", options=[(value, "List")]) is value


@pytest.mark.parametrize("defaults", [[], ["a"]])
def test_reject_multiple_defaults_in_single_mode(run_choice, defaults):
    with pytest.raises(
        ValueError, match="default_values requires multiple_selection=True"
    ):
        run_choice("\r", default_values=defaults)


@pytest.mark.parametrize("multiple_selection", [False, True])
def test_empty_options(run_choice, multiple_selection):
    with pytest.raises(AssertionError):
        run_choice("\r", options=[], multiple_selection=multiple_selection)


def test_custom_interrupt_exception(run_choice):
    with pytest.raises(RuntimeError):
        run_choice("\x03", multiple_selection=True, interrupt_exception=RuntimeError)


def test_disabled_interrupt(run_choice):
    result = run_choice("\x03 \r", multiple_selection=True, enable_interrupt=False)
    assert result == ["a"]


def test_custom_key_bindings(run_choice):
    bindings = KeyBindings()

    @bindings.add("c-x")
    def accept_custom(event):
        event.app.exit(result=["custom"])

    result = run_choice("\x18", multiple_selection=True, key_bindings=bindings)
    assert result == ["custom"]


@pytest.mark.parametrize("show_frame", [False, True])
def test_formatted_options_frame_and_toolbar(run_choice, show_frame):
    assert run_choice(
        "2 \r",
        options=[("a", HTML("<b>Alpha</b>")), ("b", HTML("<i>Bravo</i>"))],
        multiple_selection=True,
        show_frame=show_frame,
        bottom_toolbar=lambda: HTML("<b>Space</b> toggles; Enter accepts"),
    ) == ["b"]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_reusing_input_does_not_reuse_selection(mock_input, asynchronous):
    selection = ChoiceInput(message="Choose:", options=OPTIONS)
    if asynchronous:

        async def run():
            mock_input.send_text(" \r")
            assert await selection.prompt_async(multiple_selection=True) == ["a"]
            mock_input.send_text("\r")
            assert await selection.prompt_async(multiple_selection=True) == []
            mock_input.send_text("2\r")
            assert await selection.prompt_async() == "b"

        asyncio.run(asyncio.wait_for(run(), timeout=2))
    else:
        mock_input.send_text(" \r")
        assert selection.prompt(multiple_selection=True) == ["a"]
        mock_input.send_text("\r")
        assert selection.prompt(multiple_selection=True) == []
        mock_input.send_text("2\r")
        assert selection.prompt() == "b"


@pytest.mark.parametrize("show_numbers, expected", [(False, ["a"]), (True, ["b"])])
def test_numbers_can_be_hidden(mock_input, show_numbers, expected):
    selection = ChoiceInput(
        message="Choose:", options=OPTIONS, show_numbers=show_numbers
    )
    mock_input.send_text("2 \r")
    assert selection.prompt(multiple_selection=True) == expected


def test_mouse_toggles_without_accepting(mock_input):
    selection = ChoiceInput(message="Choose:", options=OPTIONS, mouse_support=True)
    app = selection._create_multiple_application(None)
    fragments = to_formatted_text(app.layout.current_control.text)
    handler = fragments[0][2]
    for row in [1, 2, 1]:
        handler(
            MouseEvent(
                position=Point(x=1, y=row),
                event_type=MouseEventType.MOUSE_UP,
                button=MouseButton.LEFT,
                modifiers=frozenset(),
            )
        )
    mock_input.send_text("\r")
    assert app.run() == ["c"]


def test_focus_and_checked_styles_are_independent(mock_input):
    selection = ChoiceInput(
        message="Choose:", options=OPTIONS, symbol="+", style=Style.from_dict({})
    )
    app = selection._create_multiple_application(["b"])
    control = app.layout.current_control
    fragments = to_formatted_text(control.text)
    text = fragment_list_to_text(fragments)
    assert "+  2. Bravo" in text
    assert "   1. Alpha" in text
    checked = [f for f in fragments if "class:selected-option" in f[0]]
    focused = [f for f in fragments if "class:focused-option" in f[0]]
    assert checked and focused
    assert selection.style.get_attrs_for_style_str(focused[0][0]).reverse
    override = Style.from_dict({"focused-option": "underline noreverse"})
    attrs = override.get_attrs_for_style_str(focused[0][0])
    assert attrs.underline and not attrs.reverse
    assert control.show_cursor is False


def test_checkbox_list_presentation_options(mock_input):
    widget = CheckboxList(
        OPTIONS,
        show_numbers=True,
        number_style="class:test-number",
        show_cursor=False,
        show_scrollbar=False,
    )
    assert widget.show_numbers is True
    assert widget.show_scrollbar is False
    assert widget.control.show_cursor is False
    fragments = widget._get_text_fragments()
    assert any(
        "class:test-number" in style and "1." in text for style, text, _ in fragments
    )


def test_checkbox_list_defaults_unchanged(mock_input):
    widget = CheckboxList(OPTIONS)
    assert widget.show_numbers is False
    assert widget.show_scrollbar is True
    assert widget.control.show_cursor is True
    assert widget.current_values == []


@pytest.mark.parametrize("supported", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
def test_suspend_respects_platform_and_filter(
    run_choice, monkeypatch, supported, enabled
):
    calls = []
    monkeypatch.setattr(
        choice_input, "suspend_to_background_supported", lambda: supported
    )
    monkeypatch.setattr(
        Application, "suspend_to_background", lambda self: calls.append("suspended")
    )
    result = run_choice("\x1a \r", multiple_selection=True, enable_suspend=enabled)
    assert result == ["a"]
    assert calls == (["suspended"] if supported and enabled else [])


def test_moving_focus_does_not_change_checked_style(mock_input):
    snapshots = []
    bindings = KeyBindings()

    @bindings.add("c-x")
    def inspect_styles(event):
        fragments = to_formatted_text(event.app.layout.current_control.text)
        snapshots.append(
            {text: style for style, text, _ in fragments if text in ("Alpha", "Bravo")}
        )

    selection = ChoiceInput(message="Choose:", options=OPTIONS, key_bindings=bindings)
    mock_input.send_text("\x181\x18\r")
    assert selection.prompt(multiple_selection=True, default_values=["b"]) == ["b"]
    before, after = snapshots
    assert "class:focused-option" in before["Bravo"]
    assert "class:selected-option" in before["Bravo"]
    assert "class:focused-option" in after["Alpha"]
    assert "class:selected-option" not in after["Alpha"]
    assert "class:focused-option" not in after["Bravo"]
    assert "class:selected-option" in after["Bravo"]
