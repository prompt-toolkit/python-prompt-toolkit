"""Vertical menu widget"""

from typing import Callable, Iterable, Optional, Tuple

from prompt_toolkit.application import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout.containers import Container, Window

from .vertmenuuicontrol import Item, VertMenuUIControl

E = KeyPressEvent


class VertMenu:
    def __init__(
        self,
        items: Iterable[Item],
        selected_item: Optional[Item] = None,
        selected_handler: Optional[
            Callable[[Optional[Item], Optional[int]], None]
        ] = None,
        accept_handler: Optional[Callable[[Item], None]] = None,
        focusable: bool = True,
        max_width: Optional[int] = None,
    ):
        self.accept_handler = accept_handler
        self.control = VertMenuUIControl(
            items,
            focusable=focusable,
            key_bindings=self._init_key_bindings(),
            selected_handler=selected_handler,
        )
        self.max_width = max_width
        self.window = Window(
            self.control, width=self.preferred_width, style=self.get_style
        )
        self.focus_window: Container = self.window
        if selected_item is not None:
            self.control.selected_item = selected_item

    def _init_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("c-home")
        @kb.add("escape", "home")
        @kb.add("c-pageup")
        def _first(event: E) -> None:
            self.control.go_first()

        @kb.add("c-end")
        @kb.add("escape", "end")
        @kb.add("c-pagedown")
        def _last(event: E) -> None:
            self.control.go_last()

        @kb.add("up")
        def _up(event: E) -> None:
            self.control.go_relative(-1)

        @kb.add("down")
        def _down(event: E) -> None:
            self.control.go_relative(1)

        @kb.add("pageup")
        def _pageup(event: E) -> None:
            w = self.window
            if w.render_info:
                self.control.go_relative(-len(w.render_info.displayed_lines))

        @kb.add("pagedown")
        def _pagedown(event: E) -> None:
            w = self.window
            if w.render_info:
                self.control.go_relative(len(w.render_info.displayed_lines))

        @kb.add(" ")
        @kb.add("enter")
        def _enter(event: E) -> None:
            self.handle_accept()

        return kb

    def get_style(self) -> str:
        if get_app().layout.has_focus(self.focus_window):
            return "class:vertmenu.focused"
        else:
            return "class:vertmenu.unfocused"

    def handle_selected(self) -> None:
        self.control.handle_selected()

    def handle_accept(self) -> None:
        if self.accept_handler is not None and self.control.selected_item is not None:
            self.accept_handler(self.control.selected_item)

    def preferred_width(self) -> int:
        width = self.control.preferred_width(0)
        assert width
        if self.max_width is not None:
            return min(width, self.max_width)
        return width

    @property
    def items(self) -> Tuple[Item, ...]:
        return self.control.items

    @items.setter
    def items(self, items: Iterable[Item]) -> None:
        self.control.items = tuple(items)

    @property
    def selected(self) -> Optional[int]:
        return self.control.selected

    @selected.setter
    def selected(self, selected: int) -> None:
        self.control.selected = selected

    @property
    def selected_item(self) -> Optional[Item]:
        return self.control.selected_item

    @selected_item.setter
    def selected_item(self, item: Item) -> None:
        self.control.selected_item = item

    @property
    def selected_handler(self) -> Optional[Callable[[Optional[Item], int], None]]:
        return self.control.selected_handler

    @selected_handler.setter
    def selected_handler(
        self,
        selected_handler: Optional[Callable[[Optional[Item], Optional[int]], None]],
    ) -> None:
        self.control.selected_handler = selected_handler

    def __pt_container__(self) -> Container:
        return self.window


__all__ = [
    "VertMenu",
    "Item",
]
