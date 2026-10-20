from prompt_toolkit.buffer import CompletionState
from prompt_toolkit.clipboard import ClipboardData, InMemoryClipboard
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import PromptSession


def test_ctrl_y_yanks_text_killed_by_ctrl_u_in_vi_insert_mode():
    with create_pipe_input() as inp:
        inp.send_text("hello\x15\x19\r")
        session = PromptSession(
            input=inp,
            output=DummyOutput(),
            editing_mode=EditingMode.VI,
            clipboard=InMemoryClipboard(),
        )
        result = session.prompt()

    assert result == "hello"


def test_ctrl_y_still_accepts_active_completion_in_vi_insert_mode():
    clipboard = InMemoryClipboard(ClipboardData("clipboard text"))

    with create_pipe_input() as inp:
        inp.send_text("\x19\r")
        session = PromptSession(
            input=inp,
            output=DummyOutput(),
            editing_mode=EditingMode.VI,
            clipboard=clipboard,
        )

        def activate_completion() -> None:
            buffer = session.default_buffer
            buffer.document = Document("he", 2)
            buffer.complete_state = CompletionState(
                buffer.document,
                [Completion("hello", start_position=-2)],
            )
            buffer.go_to_completion(0)

        result = session.prompt(pre_run=activate_completion)

    assert result == "hello"
    assert clipboard.get_data().text == "clipboard text"


def test_custom_ctrl_y_binding_overrides_vi_default():
    bindings = KeyBindings()

    @bindings.add("c-y")
    def custom_ctrl_y(event):
        event.current_buffer.insert_text("CUSTOM")

    with create_pipe_input() as inp:
        inp.send_text("\x19\r")
        session = PromptSession(
            input=inp,
            output=DummyOutput(),
            editing_mode=EditingMode.VI,
            key_bindings=bindings,
        )
        result = session.prompt()

    assert result == "CUSTOM"
