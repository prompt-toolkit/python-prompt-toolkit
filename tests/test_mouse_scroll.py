from __future__ import unicode_literals

from prompt_toolkit.layout.screen import Screen, WritePosition
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.buffer import Buffer

import pytest

def scroll(window, dim, direction, count, delay_update=True):
    for i in range(count):
        if direction == "up":
            window._scroll_up()
        elif direction == "down":
            window._scroll_down()
        else:
            # Just make sure we don't do this on accident
            assert False
        if not delay_update:
            update(window, dim)

    if delay_update:
        update(window, dim)


def update(window, dim):
    window.write_to_screen(Screen(),
                           MouseHandlers(),
                           WritePosition(xpos=0,
                                         ypos=0,
                                         width=dim["win_width"],
                                         height=dim["win_height"]),
                           parent_style='',
                           erase_bg=False,
                           z_index=None)


def check_scroll(window, expected_vertical_scroll, expected_cursor_y):
    assert window.vertical_scroll == expected_vertical_scroll
    assert window.render_info.ui_content.cursor_position.y == expected_cursor_y


@pytest.fixture
def dim():
    return { "base_width":9,
             "win_width":10,
             "win_height":4,
             "buf_height": 40 }


@pytest.fixture
def empty_window(dim):
    win = Window(content=BufferControl(buffer=Buffer()))
    win.reset()
    update(win, dim)
    assert win.vertical_scroll == 0
    assert win.render_info.ui_content.cursor_position.y == 0
    return win


def test_empty_window(empty_window, dim):
    scroll(empty_window, dim, "down", 1)
    check_scroll(empty_window, 0, 0)
    scroll(empty_window, dim, "up", 1)
    check_scroll(empty_window, 0, 0)


@pytest.fixture
def content(dim):
    buff = Buffer()
    line = "*" * (dim["base_width"])
    for i in range(dim["buf_height"] - 1):
        buff.insert_text(line)
        buff.newline()
    buff.insert_text(line)

    buff.cursor_position = 0
    control = BufferControl(buffer=buff)
    return control


@pytest.fixture
def window(content, dim):
    win = Window(content=content)
    win.reset()
    update(win, dim)
    assert win.vertical_scroll == 0
    assert win.render_info.ui_content.cursor_position.y == 0
    return win


def test_scroll_down(window, dim):
    scroll(window, dim, "down", 1, delay_update=False)
    check_scroll(window, 1, 1)

    scroll(window, dim, "down", 2, delay_update=False)
    check_scroll(window, 3, 3)

    scroll(window, dim, "down", 4, delay_update=False)
    check_scroll(window, 7, 7)

def test_scroll_up(window, dim):
    test_scroll_down(window, dim)
    scroll(window, dim, "up", 1, delay_update=False)
    check_scroll(window, 6, 7)
    scroll(window, dim, "up", 2, delay_update=False)
    check_scroll(window, 4, 7)
    scroll(window, dim, "up", 1, delay_update=False)
    check_scroll(window, 3, 6)
    scroll(window, dim, "up", 6, delay_update=False)
    check_scroll(window, 0, dim["win_height"] - 1)

def test_multiple_scroll_before_render(window, dim):
    scroll(window, dim, "down", 10)
    check_scroll(window, 10, 10)

    scroll(window, dim, "up", 1)
    scroll(window, dim, "down", 1)
    check_scroll(window, 10, 10)

def test_scroll_to_end(window, dim):
    # Regardless of how much we scroll, we should stop with the
    # last line of the window the last line of the buffer
    last_line = dim["buf_height"] - dim["win_height"]

    scroll(window, dim, "down", dim["buf_height"] * 2)
    check_scroll(window, last_line, last_line)

def test_scroll_past_end_before_render(window, dim):
    # Regardless of how much we scroll, we should stop with the
    # last line of the window the last line of the buffer
    last_line = dim["buf_height"] - dim["win_height"]

    scroll(window, dim, "down", dim["buf_height"]*2, delay_update=True)
    check_scroll(window, last_line, last_line)

@pytest.fixture
def window_allow_scroll(content, dim):
    win = Window(content=content, allow_scroll_beyond_bottom=True)
    win.reset()
    update(win, dim)
    assert win.vertical_scroll == 0
    assert win.render_info.ui_content.cursor_position.y == 0
    return win


def test_scroll_beyond_end(window_allow_scroll, dim):
    last_line = dim["buf_height"] - dim["win_height"]
    scroll(window_allow_scroll, dim, "down", last_line)
    check_scroll(window_allow_scroll, last_line, last_line)
    scroll(window_allow_scroll, dim, "down", 1)
    check_scroll(window_allow_scroll, last_line + 1, last_line + 1)
    # Max out scrolling
    scroll(window_allow_scroll, dim, "down", dim["buf_height"])
    check_scroll(window_allow_scroll, dim["buf_height"] - 1, dim["buf_height"] - 1)


@pytest.fixture
def content_line_wrap(dim):
    buff = Buffer()
    line = "*" * dim["base_width"]
    for i in range(dim["buf_height"]//2):
        buff.insert_text(line)
        buff.newline()

    for i in range(dim["buf_height"]//2 - 1):
        buff.insert_text(line * 2)
        buff.newline()
    buff.insert_text(line * 2)

    buff.cursor_position = 0
    control = BufferControl(buffer=buff)
    return control


@pytest.fixture
def window_line_wrap(content_line_wrap, dim):
    win = Window(content=content_line_wrap, wrap_lines=True)
    win.reset()
    update(win, dim)
    assert win.vertical_scroll == 0
    assert win.render_info.ui_content.cursor_position.y == 0
    return win


def test_scroll_down_with_line_wrap(window_line_wrap, dim):
    scroll(window_line_wrap, dim, "down", 1)
    check_scroll(window_line_wrap, 1, 1)

    scroll(window_line_wrap, dim, "down", 2)
    check_scroll(window_line_wrap, 3, 3)

    scroll(window_line_wrap, dim, "down", 2)
    check_scroll(window_line_wrap, 5, 5)

    mid = dim["buf_height"]//2
    # Scroll to just before change in line length
    scroll(window_line_wrap, dim, "down", mid - 5 - dim["win_height"])
    check_scroll(window_line_wrap,
                 mid - dim["win_height"],
                 mid - dim["win_height"])

    scroll(window_line_wrap, dim, "down", 1)
    check_scroll(window_line_wrap,
                 mid - dim["win_height"] + 1,
                 mid - dim["win_height"] + 1)

    scroll(window_line_wrap, dim, "down", dim["win_height"] - 1)
    check_scroll(window_line_wrap, mid, mid)

    scroll(window_line_wrap, dim, "down", 1)
    check_scroll(window_line_wrap, mid + 1, mid + 1)

def test_scroll_to_end_with_line_wrap(window_line_wrap, dim):
    # Later lines take two lines in the window
    last_line = dim["buf_height"] - dim["win_height"]//2

    scroll(window_line_wrap, dim, "down", dim["buf_height"] * 2)
    check_scroll(window_line_wrap, last_line, last_line)

@pytest.fixture
def window_allow_scroll_and_line_wrap(content_line_wrap, dim):
    win = Window(content=content_line_wrap, allow_scroll_beyond_bottom=True)
    win.reset()
    update(win, dim)
    assert win.vertical_scroll == 0
    assert win.render_info.ui_content.cursor_position.y == 0
    return win

def test_scroll_beyond_end_with_line_wrap(window_allow_scroll_and_line_wrap, dim):                               
    last_line = dim["buf_height"] - dim["win_height"]//2
    scroll(window_allow_scroll_and_line_wrap, dim, "down", last_line)
    check_scroll(window_allow_scroll_and_line_wrap, last_line, last_line)
    scroll(window_allow_scroll_and_line_wrap, dim, "down", 1)
    check_scroll(window_allow_scroll_and_line_wrap, last_line + 1, last_line + 1)
    # Max out scrolling
    scroll(window_allow_scroll_and_line_wrap, dim, "down", dim["buf_height"])
    check_scroll(window_allow_scroll_and_line_wrap, dim["buf_height"] - 1, dim["buf_height"] - 1)
