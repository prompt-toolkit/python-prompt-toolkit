"""
Margin implementations for a :class:`~prompt_toolkit.layout.containers.Window`.
"""
import asyncio
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Callable, Optional

from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.formatted_text import (
    StyleAndTextTuples,
    fragment_list_to_text,
    to_formatted_text,
)
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth

from .controls import UIContent

if TYPE_CHECKING:
    from .containers import WindowRenderInfo

__all__ = [
    "Margin",
    "NumberedMargin",
    "ScrollbarMargin",
    "ConditionalMargin",
    "PromptMargin",
]


class Margin(metaclass=ABCMeta):
    """
    Base interface for a margin.
    """

    @abstractmethod
    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int:
        """
        Return the width that this margin is going to consume.

        :param get_ui_content: Callable that asks the user control to create
            a :class:`.UIContent` instance. This can be used for instance to
            obtain the number of lines.
        """
        return 0

    @abstractmethod
    def create_margin(
        self, window_render_info: "WindowRenderInfo", width: int, height: int
    ) -> StyleAndTextTuples:
        """
        Creates a margin.
        This should return a list of (style_str, text) tuples.

        :param window_render_info:
            :class:`~prompt_toolkit.layout.containers.WindowRenderInfo`
            instance, generated after rendering and copying the visible part of
            the :class:`~prompt_toolkit.layout.controls.UIControl` into the
            :class:`~prompt_toolkit.layout.containers.Window`.
        :param width: The width that's available for this margin. (As reported
            by :meth:`.get_width`.)
        :param height: The height that's available for this margin. (The height
            of the :class:`~prompt_toolkit.layout.containers.Window`.)
        """
        return []


class NumberedMargin(Margin):
    """
    Margin that displays the line numbers.

    :param relative: Number relative to the cursor position. Similar to the Vi
                     'relativenumber' option.
    :param display_tildes: Display tildes after the end of the document, just
        like Vi does.
    """

    def __init__(
        self, relative: FilterOrBool = False, display_tildes: FilterOrBool = False
    ) -> None:

        self.relative = to_filter(relative)
        self.display_tildes = to_filter(display_tildes)

    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int:
        line_count = get_ui_content().line_count
        return max(3, len("%s" % line_count) + 1)

    def create_margin(
        self, window_render_info: "WindowRenderInfo", width: int, height: int
    ) -> StyleAndTextTuples:
        relative = self.relative()

        style = "class:line-number"
        style_current = "class:line-number.current"

        # Get current line number.
        current_lineno = window_render_info.ui_content.cursor_position.y

        # Construct margin.
        result: StyleAndTextTuples = []
        last_lineno = None

        for y, lineno in enumerate(window_render_info.displayed_lines):
            # Only display line number if this line is not a continuation of the previous line.
            if lineno != last_lineno:
                if lineno is None:
                    pass
                elif lineno == current_lineno:
                    # Current line.
                    if relative:
                        # Left align current number in relative mode.
                        result.append((style_current, "%i" % (lineno + 1)))
                    else:
                        result.append(
                            (style_current, ("%i " % (lineno + 1)).rjust(width))
                        )
                else:
                    # Other lines.
                    if relative:
                        lineno = abs(lineno - current_lineno) - 1

                    result.append((style, ("%i " % (lineno + 1)).rjust(width)))

            last_lineno = lineno
            result.append(("", "\n"))

        # Fill with tildes.
        if self.display_tildes():
            while y < window_render_info.window_height:
                result.append(("class:tilde", "~\n"))
                y += 1

        return result


class ConditionalMargin(Margin):
    """
    Wrapper around other :class:`.Margin` classes to show/hide them.
    """

    def __init__(self, margin: Margin, filter: FilterOrBool) -> None:
        self.margin = margin
        self.filter = to_filter(filter)

    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int:
        if self.filter():
            return self.margin.get_width(get_ui_content)
        else:
            return 0

    def create_margin(
        self, window_render_info: "WindowRenderInfo", width: int, height: int
    ) -> StyleAndTextTuples:
        if width and self.filter():
            return self.margin.create_margin(window_render_info, width, height)
        else:
            return []


class ScrollbarMargin(Margin):
    """
    Margin displaying a scrollbar.

    :param display_arrows: Display scroll up/down arrows.
    :param up_arrow: Character to use for the scrollbar's up arrow
    :param down_arrow: Character to use for the scrollbar's down arrow
    :param smooth: Use block character to move scrollbar more smoothly
    """

    window_render_info: "WindowRenderInfo"

    eighths = "█▇▆▅▄▃▂▁ "

    def __init__(
        self,
        display_arrows: "FilterOrBool" = True,
        up_arrow_symbol: "str" = "▲",
        down_arrow_symbol: "str" = "▼",
        smooth: "bool" = True,
    ) -> None:

        self.display_arrows = to_filter(display_arrows)
        self.up_arrow_symbol = up_arrow_symbol
        self.down_arrow_symbol = down_arrow_symbol
        self.smooth = smooth

        self.repeat_task: Optional[asyncio.Task[None]] = None
        self.dragging = False
        self.button_drag_offset = 0

        self.thumb_top = 0.0
        self.thumb_size = 0.0

    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int:
        """Return the scrollbar width: always 1."""
        return 1

    def create_margin(
        self, window_render_info: "WindowRenderInfo", width: int, height: int
    ) -> StyleAndTextTuples:

        result: StyleAndTextTuples = []

        self.window_render_info = window_render_info

        # Show we render the arrow buttons?
        display_arrows = self.display_arrows()

        # The height of the scrollbar, excluding the optional buttons
        self.track_height = window_render_info.window_height
        if display_arrows:
            self.track_height -= 2

        # Height of all text in the output: If there is none, we cannot divide by zero
        # so we do not display a thumb
        content_height = window_render_info.content_height
        if content_height == 0 or content_height <= len(
            window_render_info.displayed_lines
        ):
            self.thumb_size = 0.0
        else:
            # The thumb is the part which moves, floating on the track: calculate its size
            fraction_visible = len(window_render_info.displayed_lines) / (
                content_height
            )
            self.thumb_size = (
                int(
                    min(self.track_height, max(1, self.track_height * fraction_visible))
                    * 8
                )
                / 8
            )
        if not self.smooth:
            self.thumb_size = int(self.thumb_size)

        # Calculate the position of the thumb
        if content_height <= len(window_render_info.displayed_lines):
            fraction_above = 0.0
        else:
            fraction_above = window_render_info.vertical_scroll / (
                content_height - len(window_render_info.displayed_lines)
            )
        # Do not allow the thumb to move beyond the ends of the track
        self.thumb_top = max(
            0,
            min(
                self.track_height - self.thumb_size,
                (int((self.track_height - self.thumb_size) * fraction_above * 8) / 8),
            ),
        )
        if not self.smooth:
            self.thumb_top = int(self.thumb_top)

        # Determine which characters to use for the ends of the thumb
        thumb_top_char = self.eighths[int(self.thumb_top % 1 * 8)]
        thumb_bottom_char = self.eighths[
            int((self.thumb_top + self.thumb_size) % 1 * 8)
        ]

        # Calculate thumb dimensions
        show_thumb_top = (self.thumb_top % 1) != 0
        thumb_top_size = 1 - self.thumb_top % 1
        show_thumb_bottom = (self.thumb_top + self.thumb_size) % 1 != 0
        thumb_bottom_size = (self.thumb_top + self.thumb_size) % 1
        thumb_middle_size = int(
            self.thumb_size
            - show_thumb_top * thumb_top_size
            - show_thumb_bottom * thumb_bottom_size
        )
        rows_after_thumb = (
            self.track_height
            - int(self.thumb_top)
            - show_thumb_top
            - thumb_middle_size
            - show_thumb_bottom
        )

        # Construct the scrollbar

        # Up button
        if display_arrows:
            result += [
                ("class:scrollbar.arrow", self.up_arrow_symbol, self.mouse_handler),
                ("class:scrollbar", "\n", self.mouse_handler),
            ]
        # Track above the thumb
        for _ in range(int(self.thumb_top)):
            result += [
                ("class:scrollbar.background", " ", self.mouse_handler),
                ("class:scrollbar", "\n", self.mouse_handler),
            ]
        # Top of thumb
        if show_thumb_top:
            result += [
                (
                    "class:scrollbar.background,scrollbar.start",
                    thumb_top_char,
                    self.mouse_handler,
                ),
                ("class:scrollbar", "\n", self.mouse_handler),
            ]
        # Middle of thumb
        for _ in range(thumb_middle_size):
            result += [
                ("class:scrollbar.button", " ", self.mouse_handler),
                ("class:scrollbar", "\n", self.mouse_handler),
            ]
        # Bottom of thumb
        if show_thumb_bottom:
            result += [
                (
                    "class:scrollbar.background,scrollbar.end",
                    thumb_bottom_char,
                    self.mouse_handler,
                ),
                ("class:scrollbar", "\n", self.mouse_handler),
            ]
        # Track below the thumb
        for _ in range(rows_after_thumb):
            result += [
                ("class:scrollbar.background", " ", self.mouse_handler),
                ("class:scrollbar", "\n", self.mouse_handler),
            ]
        # Down button
        if display_arrows:
            result += [
                ("class:scrollbar.arrow", self.down_arrow_symbol, self.mouse_handler),
            ]

        return result

    def mouse_handler(
        self, mouse_event: MouseEvent, repeated: "bool" = False
    ) -> "None":
        """Handle scrollbar mouse events.

        Scrolls up or down if the arrows are clicked, repeating while the mouse button
        is held down. Scolls up or down one page if the background is clicked,
        repeating while the left mouse button is held down. Scrolls if the
        scrollbar-button is dragged. Scrolls if the scroll-wheel is used on the
        scrollbar.

        Args:
            mouse_event: The triggering mouse event
            repeated: Set to True if the method is running as a repeated event

        """
        row = mouse_event.position.y

        content_height = self.window_render_info.content_height

        # Handle scroll events on the scrollbar
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            self.window_render_info.window._scroll_up()
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self.window_render_info.window._scroll_down()

        # Mouse drag events
        elif self.dragging and mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            # Scroll so the button gets moved to where the mouse is
            offset = int(
                (row - self.thumb_top - self.button_drag_offset)
                / self.track_height
                * content_height
            )
            if offset < 0:
                func = self.window_render_info.window._scroll_up
            else:
                func = self.window_render_info.window._scroll_down
            if func:
                # Scroll the window multiple times to scroll by the offset
                for _ in range(abs(offset)):
                    func()

        # Mouse down events
        elif mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            # Scroll up/down one line if clicking on the arrows
            arrows = self.display_arrows()
            if arrows and row == 0:
                offset = -1
            elif arrows and row == self.window_render_info.window_height - 1:
                offset = 1
            # Scroll up or down one page if clicking on the background
            elif row < self.thumb_top or self.thumb_top + self.thumb_size < row:
                direction = (row < (self.thumb_top + self.thumb_size // 2)) * -2 + 1
                offset = direction * self.window_render_info.window_height
            # We are on the scroll button - start a drag event if this is not a
            # repeated mouse event
            elif not repeated:
                self.dragging = True
                self.button_drag_offset = mouse_event.position.y - int(self.thumb_top)
                return
            # Otherwise this is a click on the centre scroll button - do nothing
            else:
                offset = 0

            if mouse_event.button == MouseButton.LEFT:
                func = None
                if offset < 0:
                    func = self.window_render_info.window._scroll_up
                elif offset > 0:
                    func = self.window_render_info.window._scroll_down
                if func:
                    # Scroll the window multiple times to scroll by the offset
                    for _ in range(abs(offset)):
                        func()
                    # Trigger this mouse event to be repeated
                    self.repeat_task = get_app().create_background_task(
                        self.repeat(mouse_event)
                    )

        # Handle all other mouse events
        else:
            # Stop any repeated tasks
            if self.repeat_task is not None:
                self.repeat_task.cancel()
            # Cancel drags
            self.dragging = False

    async def repeat(self, mouse_event: MouseEvent, timeout: float = 0.1) -> "None":
        """Repeat a mouse event after a timeout."""
        await asyncio.sleep(timeout)
        self.mouse_handler(mouse_event, repeated=True)
        get_app().invalidate()


class PromptMargin(Margin):
    """
    [Deprecated]

    Create margin that displays a prompt.
    This can display one prompt at the first line, and a continuation prompt
    (e.g, just dots) on all the following lines.

    This `PromptMargin` implementation has been largely superseded in favor of
    the `get_line_prefix` attribute of `Window`. The reason is that a margin is
    always a fixed width, while `get_line_prefix` can return a variable width
    prefix in front of every line, making it more powerful, especially for line
    continuations.

    :param get_prompt: Callable returns formatted text or a list of
        `(style_str, type)` tuples to be shown as the prompt at the first line.
    :param get_continuation: Callable that takes three inputs. The width (int),
        line_number (int), and is_soft_wrap (bool). It should return formatted
        text or a list of `(style_str, type)` tuples for the next lines of the
        input.
    """

    def __init__(
        self,
        get_prompt: Callable[[], StyleAndTextTuples],
        get_continuation: Optional[
            Callable[[int, int, bool], StyleAndTextTuples]
        ] = None,
    ) -> None:

        self.get_prompt = get_prompt
        self.get_continuation = get_continuation

    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int:
        "Width to report to the `Window`."
        # Take the width from the first line.
        text = fragment_list_to_text(self.get_prompt())
        return get_cwidth(text)

    def create_margin(
        self, window_render_info: "WindowRenderInfo", width: int, height: int
    ) -> StyleAndTextTuples:
        get_continuation = self.get_continuation
        result: StyleAndTextTuples = []

        # First line.
        result.extend(to_formatted_text(self.get_prompt()))

        # Next lines.
        if get_continuation:
            last_y = None

            for y in window_render_info.displayed_lines[1:]:
                result.append(("", "\n"))
                result.extend(
                    to_formatted_text(get_continuation(width, y, y == last_y))
                )
                last_y = y

        return result
