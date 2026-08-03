"""Vertical menu widget UIControl"""

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    NewType,
    Optional,
    Tuple,
    cast,
)

from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.formatted_text import (
    AnyFormattedText,
    StyleAndTextTuples,
    split_lines,
    to_formatted_text,
    to_plain_text,
)
from prompt_toolkit.key_binding.key_bindings import KeyBindingsBase
from prompt_toolkit.layout.controls import GetLinePrefixCallable, UIContent, UIControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone

Item = Tuple[AnyFormattedText, Any]
Index = NewType("Index", int)


class VertMenuUIControl(UIControl):
    """UIControl optimized for VertMenu"""

    def __init__(
        self,
        items: Iterable[Item],
        focusable: FilterOrBool = True,
        key_bindings: Optional[KeyBindingsBase] = None,
        selected_handler: Optional[
            Callable[[Optional[Item], Optional[int]], None]
        ] = None,
    ):
        self._items = tuple(items)
        self._selected: Optional[Index] = Index(0)
        self.focusable = to_filter(focusable)
        self.key_bindings = key_bindings
        self.selected_handler = selected_handler
        self._width = 30
        # Mark if the last movement we did was down:
        self._moved_down = False
        # ^ We use this to show the complete label of the item at the
        # bottom of the screen when it's the selected one.
        self._lineno_to_index: Dict[int, Index] = {}
        self._index_to_lineno: Dict[Index, int] = {}
        self._gen_lineno_mappings()
        self.handle_selected()

    def handle_selected(self) -> None:
        if self.selected_handler is not None:
            self.selected_handler(self.selected_item, self.selected)

    def _items_enumerate(self) -> Iterator[Tuple[Index, Item]]:
        for index, item in enumerate(self._items):
            yield Index(index), item

    def _gen_lineno_mappings(self) -> None:
        # Create the lineno <-> item mappings:
        self._lineno_to_index.clear()
        self._index_to_lineno.clear()
        lineno = 0
        self._width = 30
        for index, item in self._items_enumerate():
            self._index_to_lineno[Index(index)] = lineno
            for formatted_line in split_lines(to_formatted_text(item[0])):
                line = to_plain_text(formatted_line)
                self._lineno_to_index[lineno] = index
                lineno += 1
                self._width = max(self._width, len(line))

    @property
    def items(self) -> Tuple[Item, ...]:
        return self._items

    @items.setter
    def items(self, items: Iterable[Item]) -> None:
        previous = None
        if self._items and self._selected is not None:
            previous = self._items[self._selected]
        self._items = tuple(items)
        if self._items:
            self._selected = Index(0)
        else:
            self._selected = None
        self._moved_down = False
        self._gen_lineno_mappings()
        if previous is None:
            self.handle_selected()
            return
        # We keep the same selected item, if possible:
        try:
            self.selected_item = previous
        except IndexError:
            # Not possible, let's just handle the current item:
            self.handle_selected()

    @property
    def selected(self) -> Optional[int]:
        if self._selected is None or not self._items:
            return None
        return cast(int, self._selected)

    @selected.setter
    def selected(self, selected: Optional[int]) -> None:
        previous = self._selected
        if selected is None:
            self._selected = None
        else:
            selected = max(0, selected)
            selected = min(selected, len(self._items) - 1)
            self._selected = Index(selected)
            if previous is not None:
                self._moved_down = self._selected > previous
        if self._selected != previous:
            self.handle_selected()

    @property
    def selected_item(self) -> Optional[Item]:
        if self._selected is None or not self._items:
            return None
        return self._items[self._selected]

    @selected_item.setter
    def selected_item(self, item: Optional[Item]) -> None:
        if item is None:
            self._selected = None
            return
        for index, current in self._items_enumerate():
            if current == item:
                self._selected = index
                return
        raise IndexError

    def preferred_width(self, max_available_width: int) -> Optional[int]:
        return self._width

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: Optional[GetLinePrefixCallable],
    ) -> Optional[int]:
        return len(self._lineno_to_index)

    def is_focusable(self) -> bool:
        return self.focusable()

    def _get_line(self, lineno: int) -> StyleAndTextTuples:
        index = self._lineno_to_index[lineno]
        item = self._items[index]
        itemlines = list(split_lines(to_formatted_text(item[0])))
        line = itemlines[lineno - self._index_to_lineno[index]]
        if self.selected_item == item:
            style = "class:vertmenu.selected"
        else:
            style = "class:vertmenu.item"
        return [(frag[0] + " " + style if frag[0] else style, frag[1]) for frag in line]

    def _cursor_position(self) -> Point:
        item = self.selected_item
        if item is None:
            return Point(x=0, y=0)
        if self._selected is None:
            return Point(x=0, y=0)
        lineno = self._index_to_lineno[self._selected]
        if self._moved_down:
            # Put the cursor in the last line of a multi-line item if
            # we have moved down to show the full label if it is at
            # the bottom of the screen:
            while self._lineno_to_index.get(lineno + 1) == self.selected:
                lineno += 1
        return Point(x=0, y=lineno)

    def create_content(self, width: int, height: int) -> UIContent:
        return UIContent(
            get_line=self._get_line,
            line_count=len(self._lineno_to_index),
            show_cursor=False,
            cursor_position=self._cursor_position(),
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> "NotImplementedOrNone":
        if mouse_event.event_type != MouseEventType.MOUSE_DOWN:
            return NotImplemented
        index = self._lineno_to_index.get(mouse_event.position.y)
        if index is not None:
            self.selected = index
        return None

    def move_cursor_down(self) -> None:
        self.go_relative(1)
        # Unmark _moved_down because this is only called when the
        # cursor is at the top:
        self._moved_down = False

    def move_cursor_up(self) -> None:
        self.go_relative(-1)
        # Mark _moved_down because this called when the cursor is at
        # the bottom:
        self._moved_down = True

    def get_key_bindings(self) -> Optional[KeyBindingsBase]:
        return self.key_bindings

    def go_first(self) -> None:
        if not self._items:
            self._selected = None
            return
        self.selected = 0

    def go_last(self) -> None:
        if not self._items:
            self._selected = None
            return
        self.selected = len(self.items) - 1

    def go_relative(self, positions: int) -> None:
        if not self._items:
            self._selected = None
            return
        if self.selected is None:
            self.selected = 0
        else:
            self.selected += positions
