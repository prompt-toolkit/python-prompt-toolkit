"""ptvertmenuuicontrol tests"""

import unittest
from typing import List

from prompt_toolkit.data_structures import Point
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.widgets.vertmenuuicontrol import Item, VertMenuUIControl


def mouse_click(lineno: int) -> MouseEvent:
    return MouseEvent(
        Point(x=0, y=lineno), MouseEventType.MOUSE_DOWN, MouseButton.LEFT, frozenset()
    )


class TestVertMenuUIControlSingle(unittest.TestCase):
    def setUp(self) -> None:
        self.items = [
            (item, item) for item in ["breakfast", "lunch", "dinner", "midnight"]
        ]
        self.control = VertMenuUIControl(self.items)

    def test_methods(self) -> None:
        """Just call all methods and let exceptions fail"""
        self.control.items = self.control.items
        self.control.selected = self.control.selected
        self.control.selected_item = self.control.selected_item
        self.control.preferred_width(999)
        self.control.preferred_height(999, 999, False, None)
        self.control.is_focusable()
        for i in range(len(self.items)):
            self.control._get_line(i)
        self.control._cursor_position()
        self.control.create_content(30, len(self.items))
        self.control.mouse_handler(mouse_click(0))
        self.control.move_cursor_down()
        self.control.move_cursor_up()
        self.control.get_key_bindings()

    def check_lines(self, selected: int) -> None:
        self.assertEqual(selected, self.control.selected)
        self.assertEqual(selected, self.control._cursor_position().y)
        self.assertEqual(self.items[selected], self.control.selected_item)
        lines = [self.control._get_line(i) for i in range(len(self.items))]
        for lineno, line in enumerate(lines):
            # Each line has one fragment
            self.assertEqual(len(line), 1)
            # The fragment is a tuple: (style, text)
            self.assertEqual(len(line[0]), 2)
            if lineno == selected:
                self.assertEqual(line[0][0], "class:vertmenu.selected")
            else:
                self.assertEqual(line[0][0], "class:vertmenu.item")

    def test_default(self) -> None:
        self.assertTrue(self.control.is_focusable())
        self.assertEqual(self.control.selected, 0)
        self.assertEqual(self.control.selected_item, ("breakfast", "breakfast"))
        self.check_lines(0)

    def test_dimensions(self) -> None:
        self.assertEqual(self.control.preferred_width(999), 30)
        self.assertEqual(
            self.control.preferred_height(999, 999, False, None), len(self.items)
        )

    def test_selected(self) -> None:
        assert self.control.selected is not None
        self.control.selected += 1
        self.assertEqual(self.control.selected, 1)
        self.assertEqual(self.control.selected_item, ("lunch", "lunch"))
        self.check_lines(1)

    def test_selected_item(self) -> None:
        self.control.selected_item = ("dinner", "dinner")
        self.assertEqual(self.control.selected, 2)
        self.assertEqual(self.control.selected_item, ("dinner", "dinner"))
        self.check_lines(2)

    def test_selected_item_invalid(self) -> None:
        with self.assertRaises(IndexError):
            self.control.selected_item = ("Sunday", "Sunday")
        self.check_lines(0)

    def test_selected_limits(self) -> None:
        self.control.selected = -1
        self.assertEqual(self.control.selected, 0)
        self.control.selected = len(self.items) + 1
        self.assertEqual(self.control.selected, len(self.items) - 1)

    def test_items(self) -> None:
        self.control.selected = 1
        self.assertEqual(self.control.selected_item, ("lunch", "lunch"))
        self.control.items = tuple(self.items[:2])
        self.assertEqual(self.control.items, tuple(self.items[:2]))
        self.assertEqual(self.control.selected, 1)
        self.assertEqual(self.control.selected_item, ("lunch", "lunch"))
        self.control.items = tuple(self.items[1:])
        self.assertEqual(self.control.selected, 0)
        self.assertEqual(self.control.selected_item, ("lunch", "lunch"))
        self.control.items = tuple([self.items[0]] + self.items[2:])
        self.assertEqual(self.control.selected, 0)
        self.assertEqual(self.control.selected_item, ("breakfast", "breakfast"))
        self.control.items = ()
        self.assertEqual(self.control.selected, None)
        self.assertEqual(self.control.selected_item, None)
        self.control.items = tuple(self.items)
        self.assertEqual(self.control.items, tuple(self.items))
        self.assertEqual(self.control.selected, 0)
        self.assertEqual(self.control.selected_item, ("breakfast", "breakfast"))

    def test_items_width_update(self) -> None:
        bigitem = ", ".join(str(i) for i in range(50))
        self.control.items = ((bigitem, bigitem),)
        width = self.control.preferred_width(999)
        self.assertEqual(width, len(bigitem))
        # Check if using a smaller bigitem updates the width
        bigitem = ", ".join(str(i) for i in range(30))
        self.control.items = ((bigitem, bigitem),)
        width = self.control.preferred_width(999)
        self.assertEqual(width, len(bigitem))

    def test_select_none(self) -> None:
        self.control.selected = None
        self.assertEqual(self.control.selected_item, None)

    def test_select_item_none(self) -> None:
        self.control.selected_item = None
        self.assertEqual(self.control.selected, None)

    def test_mouse(self) -> None:
        for i in range(len(self.items)):
            self.control.mouse_handler(mouse_click(i))
            self.check_lines(i)


class TestVertMenuUIControlEmpty(unittest.TestCase):
    def setUp(self) -> None:
        self.items: tuple[Item, ...] = ()
        self.control = VertMenuUIControl(self.items)

    def test_methods(self) -> None:
        """Just call all methods and let exceptions fail"""
        self.control.items = self.control.items
        self.assertEqual(self.control.selected, None)
        self.control.selected = self.control.selected
        self.assertEqual(self.control.selected_item, None)
        self.control.selected_item = None
        self.control.preferred_width(999)
        self.control.preferred_height(999, 999, False, None)
        self.control.is_focusable()
        with self.assertRaises(KeyError):
            self.control._get_line(0)
        self.control._cursor_position()
        self.control.create_content(30, len(self.items))
        self.control.mouse_handler(mouse_click(0))
        self.control.move_cursor_down()
        self.control.move_cursor_up()
        self.control.get_key_bindings()

    def test_dimensions(self) -> None:
        self.assertEqual(self.control.preferred_width(999), 30)
        self.assertEqual(self.control.preferred_height(999, 999, False, None), 0)


class TestVertMenuUIControlMultiLine(unittest.TestCase):
    LINES = 3

    def setUp(self) -> None:
        self.items: List[tuple[str, str]] = []
        for i in range(5):
            self.items.append((self.label(i), self.label(i)))
        self.control = VertMenuUIControl(self.items)

    def label(self, item: int) -> str:
        return "\n".join(f"item {item} line {lineno}" for lineno in range(self.LINES))

    def test_down_up(self) -> None:
        assert self.control.selected is not None
        self.control.selected += 1
        # Check that we are in the bottom line of the item:
        self.assertEqual(self.control.selected, 1)
        self.assertEqual(self.control._cursor_position().y, 5)
        # Now go down and up
        self.control.selected += 1
        self.control.selected -= 1
        # We are back in the same item, but on the first line:
        self.assertEqual(self.control._cursor_position().y, 3)

    def test_scroll_down(self) -> None:
        self.control.move_cursor_down()
        # If we scroll the first item out of the screen, we go to the
        # first line of the second item:
        self.assertEqual(self.control.selected, 1)
        self.assertEqual(self.control._cursor_position().y, 3)

    def test_scroll_up(self) -> None:
        self.control.selected = len(self.items) - 1
        # If we scroll the last item out of the screen, we go to the
        # last line of the previous item:
        self.control.move_cursor_up()
        selected = len(self.items) - 2
        self.assertEqual(self.control.selected, selected)
        lineno = self.LINES * selected + self.LINES - 1
        self.assertEqual(self.control._cursor_position().y, lineno)

    def test_mouse(self) -> None:
        for i in reversed(range(self.LINES * len(self.items))):
            self.control.mouse_handler(mouse_click(i))
            self.assertEqual(self.control.selected, i // self.LINES)
