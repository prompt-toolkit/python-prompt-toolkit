from __future__ import annotations

from typing import Generic, Sequence, TypeVar

from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition, FilterOrBool, to_filter
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout import AnyContainer, HSplit, Layout
from prompt_toolkit.styles import BaseStyle
from prompt_toolkit.utils import suspend_to_background_supported
from prompt_toolkit.widgets import Box, Frame, Label, RadioList

_T = TypeVar("_T")
E = KeyPressEvent


class InputSelection(Generic[_T]):
    def __init__(
        self,
        *,
        message: AnyFormattedText,
        options: Sequence[tuple[_T, AnyFormattedText]],
        default: _T | None = None,
        mouse_support: bool = True,
        style: BaseStyle | None = None,
        symbol: str = ">",
        show_frame: bool = False,
        enable_suspend: FilterOrBool = False,
        enable_abort: FilterOrBool = True,
        interrupt_exception: type[BaseException] = KeyboardInterrupt,
    ) -> None:
        self.message = message
        self.default = default
        self.options = options
        self.mouse_support = mouse_support
        self.style = style
        self.symbol = symbol
        self.show_frame = show_frame
        self.enable_suspend = enable_suspend
        self.interrupt_exception = interrupt_exception
        self.enable_abort = enable_abort

    def _create_application(self) -> Application[_T]:
        radio_list = RadioList(
            values=self.options,
            default=self.default,
            select_on_focus=True,
            open_character="",
            select_character=self.symbol,
            close_character="",
            show_cursor=False,
            show_numbers=True,
            container_style="class:input-selection",
            default_style="class:option",
            selected_style="",
            checked_style="class:selected-option",
            number_style="class:number",
        )
        container: AnyContainer = HSplit(
            [
                Box(
                    Label(text=self.message, dont_extend_height=True),
                    padding_top=0,
                    padding_left=1,
                    padding_right=1,
                    padding_bottom=0,
                ),
                Box(
                    radio_list,
                    padding_top=0,
                    padding_left=3,
                    padding_right=1,
                    padding_bottom=0,
                ),
            ]
        )
        if self.show_frame:
            container = Frame(container)
        layout = Layout(container, radio_list)

        kb = KeyBindings()

        @kb.add("enter", eager=True)
        def _accept_input(event: E) -> None:
            "Accept input when enter has been pressed."
            event.app.exit(result=radio_list.current_value)

        @Condition
        def enable_abort() -> bool:
            return to_filter(self.enable_abort)()

        @kb.add("c-c", filter=enable_abort)
        @kb.add("<sigint>", filter=enable_abort)
        def _keyboard_interrupt(event: E) -> None:
            "Abort when Control-C has been pressed."
            event.app.exit(exception=self.interrupt_exception(), style="class:aborting")

        suspend_supported = Condition(suspend_to_background_supported)

        @Condition
        def enable_suspend() -> bool:
            return to_filter(self.enable_suspend)()

        @kb.add("c-z", filter=suspend_supported & enable_suspend)
        def _suspend(event: E) -> None:
            """
            Suspend process to background.
            """
            event.app.suspend_to_background()

        return Application(
            layout=layout,
            full_screen=False,
            mouse_support=self.mouse_support,
            key_bindings=kb,
            style=self.style,
        )

    def prompt(self) -> _T:
        return self._create_application().run()

    async def prompt_async(self) -> _T:
        return await self._create_application().run_async()


def select_input(
    message: AnyFormattedText,
    options: Sequence[tuple[_T, AnyFormattedText]],
    default: _T | None = None,
    mouse_support: bool = True,
    style: BaseStyle | None = None,
    symbol: str = ">",
    show_frame: bool = False,
    enable_suspend: FilterOrBool = False,
    enable_abort: FilterOrBool = True,
) -> _T:
    return InputSelection(
        message=message,
        options=options,
        default=default,
        mouse_support=mouse_support,
        show_frame=show_frame,
        symbol=symbol,
        style=style,
        enable_suspend=enable_suspend,
        enable_abort=enable_abort,
    ).prompt()
