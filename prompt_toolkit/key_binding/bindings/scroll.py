"""
Key bindings, for scrolling up and down through pages.

This are separate bindings, because GNU readline doesn't have them, but
they are very useful for navigating through long multiline buffers, like in
Vi, Emacs, etc...
"""
from __future__ import unicode_literals

from prompt_toolkit.layout.utils import find_window_for_buffer_name

__all__ = (
    'scroll_forward',
    'scroll_backward',
    'scroll_half_page_up',
    'scroll_half_page_down',
    'scroll_one_line_up',
    'scroll_one_line_down',
)


def _current_window_for_event(event):
    """
    Return the `Window` for the currently focussed Buffer.
    """
    return find_window_for_buffer_name(event.cli, event.cli.current_buffer_name)


def scroll_forward(event, half=False):
    """
    Scroll window down.
    """
    w = _current_window_for_event(event)
    b = event.cli.current_buffer

    if w and w.render_info:
        info = w.render_info
        ui_content = info.ui_content

        # Height to scroll.
        scroll_height = info.window_height
        if half:
            scroll_height //= 2

        # Calculate how many lines is equivalent to that vertical space.
        y = b.document.cursor_position_row + 1
        height = 0
        while y < ui_content.line_count:
            if info.wrap_lines:
                line_height = ui_content.get_height_for_line(y, info.window_width)
            else:
                line_height = 1

            if height + line_height < scroll_height:
                height += line_height
                y += 1
            else:
                break

        b.cursor_position = b.document.translate_row_col_to_index(y, 0)


def scroll_backward(event, half=False):
    """
    Scroll window up.
    """
    w = _current_window_for_event(event)
    b = event.cli.current_buffer

    if w and w.render_info:
        info = w.render_info
        ui_content = info.ui_content

        # Height to scroll.
        scroll_height = info.window_height
        if half:
            scroll_height //= 2

        # Calculate how many lines is equivalent to that vertical space.
        y = max(0, b.document.cursor_position_row - 1)
        height = 0
        while y > 0:
            if info.wrap_lines:
                line_height = ui_content.get_height_for_line(y, info.window_width)
            else:
                line_height = 1

            if height + line_height < scroll_height:
                height += line_height
                y -= 1
            else:
                break

        b.cursor_position = b.document.translate_row_col_to_index(y, 0)


def scroll_half_page_down(event):
    """
    Same as ControlF, but only scroll half a page.
    """
    scroll_forward(event, half=True)


def scroll_half_page_up(event):
    """
    Same as ControlB, but only scroll half a page.
    """
    scroll_backward(event, half=True)


def scroll_one_line_down(event):
    """
    scroll_offset += 1
    """
    w = find_window_for_buffer_name(event.cli, event.cli.current_buffer_name)
    b = event.cli.current_buffer

    if w:
        # When the cursor is at the top, move to the next line. (Otherwise, only scroll.)
        if w.render_info:
            info = w.render_info

            if w.vertical_scroll < info.content_height - info.window_height:
                if info.cursor_position.y <= info.configured_scroll_offsets.top:
                    b.cursor_position += b.document.get_cursor_down_position()

                w.vertical_scroll += 1


def scroll_one_line_up(event):
    """
    scroll_offset -= 1
    """
    w = find_window_for_buffer_name(event.cli, event.cli.current_buffer_name)
    b = event.cli.current_buffer

    if w:
        # When the cursor is at the bottom, move to the previous line. (Otherwise, only scroll.)
        if w.render_info:
            info = w.render_info

            if w.vertical_scroll > 0:
                if info.cursor_position.y >= info.window_height - 1 - info.configured_scroll_offsets.bottom:
                    b.cursor_position += b.document.get_cursor_up_position()

                # Scroll window
                w.vertical_scroll -= 1


def scroll_page_down(event):
    """
    Scroll page down. (Prefer the cursor at the top of the page, after scrolling.)
    """
    w = _current_window_for_event(event)
    b = event.cli.current_buffer

    if w and w.render_info:
        # Scroll down one page.
        top_line_index = max(w.render_info.last_visible_line(), w.vertical_scroll + 1)
        w.vertical_scroll = top_line_index

        b.cursor_position = b.document.translate_row_col_to_index(top_line_index, 0)
        b.cursor_position += b.document.get_start_of_line_position(after_whitespace=True)


def scroll_page_up(event):
    """
    Scroll page up. (Prefer the cursor at the bottom of the page, after scrolling.)
    """
            # TODO: get line by line, measure the height of each. Go up until a whole page is filled.

    w = _current_window_for_event(event)
    b = event.cli.current_buffer

    if w and w.render_info:
        # Scroll in a way that the line which is currently at the top will be
        # displayed at the bottom. The cursor should always be visible at the bottom.
        # XXX

        # Scroll down one page.
        w.vertical_scroll = max(0, w.vertical_scroll - w.render_info.window_height)

        # Put cursor at the bottom of the visible region.
        try:
            new_document_line = w.render_info.screen_line_to_input_line[
                w.vertical_scroll + w.render_info.window_height - 1]
        except KeyError:
            new_document_line = 0

        b.cursor_position = min(b.cursor_position,
                                b.document.translate_row_col_to_index(new_document_line, 0))
        b.cursor_position += b.document.get_start_of_line_position(after_whitespace=True)
