import math
from itertools import zip_longest
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import CompletionState
from prompt_toolkit.completion import Completion
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import (
    Condition,
    FilterOrBool,
    has_completions,
    is_done,
    to_filter,
)
from prompt_toolkit.formatted_text import (
    StyleAndTextTuples,
    fragment_list_width,
    to_formatted_text,
)
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth

from .containers import ConditionalContainer, HSplit, ScrollOffsets, Window
from .controls import GetLinePrefixCallable, UIContent, UIControl
from .dimension import Dimension
from .margins import ScrollbarMargin

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_bindings import KeyBindings

    NotImplementedOrNone = object

__all__ = [
    "CompletionsMenu",
    "MultiColumnCompletionsMenu",
]

E = KeyPressEvent


class CompletionsMenuControl(UIControl):
    """
    Helper for drawing the complete menu to the screen.

    :param scroll_offset: Number (integer) representing the preferred amount of
        completions to be displayed before and after the current one. When this
        is a very high number, the current completion will be shown in the
        middle most of the time.
    """

    # Preferred minimum size of the menu control.
    # The CompletionsMenu class defines a width of 8, and there is a scrollbar
    # of 1.)
    MIN_WIDTH = 7

    def has_focus(self) -> bool:
        return False

    def preferred_width(self, max_available_width: int) -> Optional[int]:
        complete_state = get_app().current_buffer.complete_state
        if complete_state:
            menu_width = self._get_menu_width(500, complete_state)
            menu_meta_width = self._get_menu_meta_width(500, complete_state)

            return menu_width + menu_meta_width
        else:
            return 0

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: Optional[GetLinePrefixCallable],
    ) -> Optional[int]:

        complete_state = get_app().current_buffer.complete_state
        if complete_state:
            return len(complete_state.completions)
        else:
            return 0

    def create_content(self, width: int, height: int) -> UIContent:
        """
        Create a UIContent object for this control.
        """
        complete_state = get_app().current_buffer.complete_state
        if complete_state:
            completions = complete_state.completions
            index = complete_state.complete_index  # Can be None!

            # Calculate width of completions menu.
            menu_width = self._get_menu_width(width, complete_state)
            menu_meta_width = self._get_menu_meta_width(
                width - menu_width, complete_state
            )
            show_meta = self._show_meta(complete_state)

            def get_line(i: int) -> StyleAndTextTuples:
                c = completions[i]
                is_current_completion = i == index
                result = _get_menu_item_fragments(
                    c, is_current_completion, menu_width, space_after=True
                )

                if show_meta:
                    result += self._get_menu_item_meta_fragments(
                        c, is_current_completion, menu_meta_width
                    )
                return result

            return UIContent(
                get_line=get_line,
                cursor_position=Point(x=0, y=index or 0),
                line_count=len(completions),
            )

        return UIContent()

    def _show_meta(self, complete_state: CompletionState) -> bool:
        """
        Return ``True`` if we need to show a column with meta information.
        """
        return any(c.display_meta_text for c in complete_state.completions)

    def _get_menu_width(self, max_width: int, complete_state: CompletionState) -> int:
        """
        Return the width of the main column.
        """
        return min(
            max_width,
            max(
                self.MIN_WIDTH,
                max(get_cwidth(c.display_text) for c in complete_state.completions) + 2,
            ),
        )

    def _get_menu_meta_width(
        self, max_width: int, complete_state: CompletionState
    ) -> int:
        """
        Return the width of the meta column.
        """

        def meta_width(completion: Completion) -> int:
            return get_cwidth(completion.display_meta_text)

        if self._show_meta(complete_state):
            return min(
                max_width, max(meta_width(c) for c in complete_state.completions) + 2
            )
        else:
            return 0

    def _get_menu_item_meta_fragments(
        self, completion: Completion, is_current_completion: bool, width: int
    ) -> StyleAndTextTuples:

        if is_current_completion:
            style_str = "class:completion-menu.meta.completion.current"
        else:
            style_str = "class:completion-menu.meta.completion"

        text, tw = _trim_formatted_text(completion.display_meta, width - 2)
        padding = " " * (width - 1 - tw)

        return to_formatted_text(
            cast(StyleAndTextTuples, []) + [("", " ")] + text + [("", padding)],
            style=style_str,
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> "NotImplementedOrNone":
        """
        Handle mouse events: clicking and scrolling.
        """
        b = get_app().current_buffer

        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            # Select completion.
            b.go_to_completion(mouse_event.position.y)
            b.complete_state = None

        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            # Scroll up.
            b.complete_next(count=3, disable_wrap_around=True)

        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            # Scroll down.
            b.complete_previous(count=3, disable_wrap_around=True)

        return None


def _get_menu_item_fragments(
    completion: Completion,
    is_current_completion: bool,
    width: int,
    space_after: bool = False,
) -> StyleAndTextTuples:
    """
    Get the style/text tuples for a menu item, styled and trimmed to the given
    width.
    """
    if is_current_completion:
        style_str = "class:completion-menu.completion.current %s %s" % (
            completion.style,
            completion.selected_style,
        )
    else:
        style_str = "class:completion-menu.completion " + completion.style

    text, tw = _trim_formatted_text(
        completion.display, (width - 2 if space_after else width - 1)
    )

    padding = " " * (width - 1 - tw)

    return to_formatted_text(
        cast(StyleAndTextTuples, []) + [("", " ")] + text + [("", padding)],
        style=style_str,
    )


def _trim_formatted_text(
    formatted_text: StyleAndTextTuples, max_width: int
) -> Tuple[StyleAndTextTuples, int]:
    """
    Trim the text to `max_width`, append dots when the text is too long.
    Returns (text, width) tuple.
    """
    width = fragment_list_width(formatted_text)

    # When the text is too wide, trim it.
    if width > max_width:
        result = []  # Text fragments.
        remaining_width = max_width - 3

        for style_and_ch in explode_text_fragments(formatted_text):
            ch_width = get_cwidth(style_and_ch[1])

            if ch_width <= remaining_width:
                result.append(style_and_ch)
                remaining_width -= ch_width
            else:
                break

        result.append(("", "..."))

        return result, max_width - remaining_width
    else:
        return formatted_text, width


class CompletionsMenu(ConditionalContainer):
    # NOTE: We use a pretty big z_index by default. Menus are supposed to be
    #       above anything else. We also want to make sure that the content is
    #       visible at the point where we draw this menu.
    def __init__(
        self,
        max_height: Optional[int] = None,
        scroll_offset: Union[int, Callable[[], int]] = 0,
        extra_filter: FilterOrBool = True,
        display_arrows: FilterOrBool = False,
        z_index: int = 10 ** 8,
    ) -> None:

        extra_filter = to_filter(extra_filter)
        display_arrows = to_filter(display_arrows)

        super().__init__(
            content=Window(
                content=CompletionsMenuControl(),
                width=Dimension(min=8),
                height=Dimension(min=1, max=max_height),
                scroll_offsets=ScrollOffsets(top=scroll_offset, bottom=scroll_offset),
                right_margins=[ScrollbarMargin(display_arrows=display_arrows)],
                dont_extend_width=True,
                style="class:completion-menu",
                z_index=z_index,
            ),
            # Show when there are completions but not at the point we are
            # returning the input.
            filter=has_completions & ~is_done & extra_filter,
        )


class MultiColumnCompletionMenuControl(UIControl):
    """
    Completion menu that displays all the completions in several columns.
    When there are more completions than space for them to be displayed, an
    arrow is shown on the left or right side.

    :param min_rows: indicates how many rows will be available.
        When this is larger than one, it will try to use less columns and more
        rows until this value is reached.
        Be careful passing in a too big value, if less than the given amount of
        rows are available, more columns would have been required, but
        `preferred_width` doesn't know about that and reports a too small value.
        This results in less completions displayed and additional scrolling.
        (It's a limitation of how the layout engine currently works: first the
        widths are calculated, then the heights.)
    :param max_rows: maximum height of the completion menu. Must be > 0.
    :param suggested_max_column_width: The suggested max width of a column.
        The column can still be bigger than this, but if there is place for two
        columns of this width, we will display two columns. This to avoid that
        if there is one very wide completion, that it doesn't significantly
        reduce the amount of columns.
    """

    _arrow_margin = 3  # One extra padding on the right + space for arrows.

    def __init__(
        self,
        min_rows: int = 1,
        max_rows: int = 3,  # 3 is for backward comapt.
        suggested_max_column_width: int = 30,
    ) -> None:
        assert min_rows >= 1

        self.min_rows = min_rows
        self.max_rows = max_rows
        self.suggested_max_column_width = suggested_max_column_width
        self.scroll = 0

        # results cached during current render cycle
        self._cur_num_cols = 0
        self._cur_col_width = 0
        self._cur_preferred_width = 0
        self._cur_preferred_height = 0

        # Info of last rendering.
        # FIXME: where is this used?
        self._rendered_rows = 0
        self._rendered_columns = 0
        self._total_columns = 0
        self._render_pos_to_completion: Dict[Tuple[int, int], Completion] = {}
        self._render_left_arrow = False
        self._render_right_arrow = False
        self._render_width = 0

    def reset(self) -> None:
        self.scroll = 0

    def has_focus(self) -> bool:
        return False

    def preferred_width(self, max_available_width: int) -> Optional[int]:
        """
        Preferred width: prefer to use at least min_rows, but otherwise as much
        as will fit horizontally.
        Hueristics used when scanning completions to prevent a few really wide
        ones from uglifying the menu.
        """
        complete_state = get_app().current_buffer.complete_state
        if complete_state is None:
            return 0

        self._cur_col_width = self._get_column_width(complete_state)
        self._cur_num_cols = (
            max_available_width - self._arrow_margin
        ) // self._cur_col_width
        # FIXME: doesn't obey min_rows
        self._cur_preferred_width = (
            self._arrow_margin + self._cur_num_cols * self._cur_col_width
        )
        return self._cur_preferred_width

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: Optional[GetLinePrefixCallable],
    ) -> Optional[int]:
        """
        Preferred height: as much as needed in order to display all the completions.
        """
        complete_state = get_app().current_buffer.complete_state
        if complete_state is None:
            return 0

        if width != self._cur_preferred_width:
            # does happen often
            self.preferred_width(width)

        self._cur_preferred_height = min(
            math.ceil(len(complete_state.completions) / float(self._cur_num_cols)),
            self.max_rows,
            max_available_height,
        )
        return self._cur_preferred_height

    def create_content(self, width: int, height: int) -> UIContent:
        """
        Create a UIContent object for this menu.
        """
        complete_state = get_app().current_buffer.complete_state
        if complete_state is None:
            return UIContent()

        _T = TypeVar("_T")

        def grouper(
            n: int, iterable: Iterable[_T], fillvalue: Optional[_T] = None
        ) -> Iterable[List[_T]]:
            " grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx "
            args = [iter(iterable)] * n
            return zip_longest(fillvalue=fillvalue, *args)

        def is_current_completion(completion: Completion) -> bool:
            " Returns True when this completion is the currently selected one. "
            return (
                complete_state is not None
                and complete_state.complete_index is not None
                and c == complete_state.current_completion
            )

        if width != self._cur_preferred_width:
            self.preferred_width(width)

        assert self._cur_num_cols >= 1
        assert self._cur_col_width < width
        assert (
            height <= self._cur_preferred_height
        ), "rendered height > last preferred height?"

        columns_ = list(grouper(height, complete_state.completions))
        rows_ = list(zip(*columns_))

        # Make sure the current completion is always visible: update scroll offset.
        selected_column = (complete_state.complete_index or 0) // height
        self.scroll = min(
            selected_column, max(self.scroll, selected_column - self._cur_num_cols + 1)
        )

        render_left_arrow = self.scroll > 0
        render_right_arrow = self.scroll < len(rows_[0]) - self._cur_num_cols

        # Write completions to screen.
        self._render_pos_to_completion = {}
        fragments_for_line = []

        for row_index, row in enumerate(rows_):
            fragments: StyleAndTextTuples = []
            middle_row = row_index == len(rows_) // 2

            # Draw left arrow if we have hidden completions on the left.
            if render_left_arrow:
                fragments.append(("class:scrollbar", "<" if middle_row else " "))
            elif render_right_arrow:
                # Reserve one column empty space. (If there is a right
                # arrow right now, there can be a left arrow as well.)
                fragments.append(("", " "))

            # Draw row content.
            for column_index, c in enumerate(row[self.scroll :][: self._cur_num_cols]):
                if c is not None:
                    fragments += _get_menu_item_fragments(
                        c,
                        is_current_completion(c),
                        self._cur_col_width,
                        space_after=False,
                    )

                    # Remember render position for mouse click handler.
                    for x in range(self._cur_col_width):
                        self._render_pos_to_completion[
                            (column_index * self._cur_col_width + x, row_index)
                        ] = c
                else:
                    fragments.append(("class:completion", " " * self._cur_col_width))

            # Draw trailing padding for this row.
            # (_get_menu_item_fragments only returns padding on the left.)
            if render_left_arrow or render_right_arrow:
                fragments.append(("class:completion", " "))

            # Draw right arrow if we have hidden completions on the right.
            if render_right_arrow:
                fragments.append(("class:scrollbar", ">" if middle_row else " "))
            elif render_left_arrow:
                fragments.append(("class:completion", " "))

            # Add line.
            fragments_for_line.append(
                to_formatted_text(fragments, style="class:completion-menu")
            )

        self._rendered_rows = height
        self._rendered_columns = self._cur_num_cols
        self._total_columns = len(columns_)
        self._render_left_arrow = render_left_arrow
        self._render_right_arrow = render_right_arrow
        self._render_width = (
            self._cur_col_width * self._cur_num_cols
            + render_left_arrow
            + render_right_arrow
            + 1
        )

        def get_line(i: int) -> StyleAndTextTuples:
            return fragments_for_line[i]

        return UIContent(get_line=get_line, line_count=len(rows_))

    def _get_column_width(self, complete_state: CompletionState) -> int:
        """
        Return the width of each column.
        Prevent a few very long outliers from forcing too few columns.
        Return not max but 90th percentile largest (e.g max of 9, but 2nd largest of 10)
        """

        top_n = (
            1 + len(complete_state.completions) // 10
        )  # number of top values to learn

        if top_n <= 1:  # max of 1-10 completions
            ret_val = (
                max(get_cwidth(c.display_text) for c in complete_state.completions) + 1
            )
        else:  # 90th percentile longest length of more.
            top_n_list = list([0 for i in range(top_n)])
            for c in complete_state.completions:
                cur_len = get_cwidth(c.display_text)
                if cur_len > top_n_list[0]:
                    top_n_list[0] = cur_len
                    top_n_list.sort()
            ret_val = top_n_list[0] + 1
        # FIXME: should consider self.suggested_max_column_width, too.
        return ret_val

    def mouse_handler(
        self, mouse_event: MouseEvent
    ) -> Optional["NotImplementedOrNone"]:
        """
        Handle scroll and click events.
        """
        b = get_app().current_buffer

        def scroll_left() -> None:
            b.complete_previous(count=self._rendered_rows, disable_wrap_around=True)
            self.scroll = max(0, self.scroll - 1)

        def scroll_right() -> None:
            b.complete_next(count=self._rendered_rows, disable_wrap_around=True)
            self.scroll = min(
                self._total_columns - self._rendered_columns, self.scroll + 1
            )

        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            scroll_right()

        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            scroll_left()

        elif mouse_event.event_type == MouseEventType.MOUSE_UP:
            x = mouse_event.position.x
            y = mouse_event.position.y

            # Mouse click on left arrow.
            if x == 0:
                if self._render_left_arrow:
                    scroll_left()

            # Mouse click on right arrow.
            elif x == self._render_width - 1:
                if self._render_right_arrow:
                    scroll_right()

            # Mouse click on completion.
            else:
                completion = self._render_pos_to_completion.get((x, y))
                if completion:
                    b.apply_completion(completion)

        return None

    def get_key_bindings(self) -> "KeyBindings":
        """
        Expose key bindings that handle the left/right arrow keys when the menu
        is displayed.
        """
        from prompt_toolkit.key_binding.key_bindings import KeyBindings

        kb = KeyBindings()

        @Condition
        def filter() -> bool:
            " Only handle key bindings if this menu is visible. "
            app = get_app()
            complete_state = app.current_buffer.complete_state

            # There need to be completions, and one needs to be selected.
            if complete_state is None or complete_state.complete_index is None:
                return False

            # This menu needs to be visible.
            return any(window.content == self for window in app.layout.visible_windows)

        def move(right: bool = False) -> None:
            buff = get_app().current_buffer
            complete_state = buff.complete_state

            if complete_state is not None and complete_state.complete_index is not None:
                # Calculate new complete index.
                new_index = complete_state.complete_index
                if right:
                    new_index += self._rendered_rows
                else:
                    new_index -= self._rendered_rows

                if 0 <= new_index < len(complete_state.completions):
                    buff.go_to_completion(new_index)

        # NOTE: the is_global is required because the completion menu will
        #       never be focussed.

        @kb.add("left", is_global=True, filter=filter)
        def _left(event: E) -> None:
            move()

        @kb.add("right", is_global=True, filter=filter)
        def _right(event: E) -> None:
            move(True)

        return kb


class MultiColumnCompletionsMenu(HSplit):
    """
    Container that displays the completions in several columns.
    When `show_meta` (a :class:`~prompt_toolkit.filters.Filter`) evaluates
    to True, it shows the meta information at the bottom.
    :param min_rows: is minimum number of rows in the completions window.
        meta window will add 1 additional row if it is visible.
    :param max_rows: is maximum number of rows in the completions window.
        Must be > 0.

    """

    def __init__(
        self,
        min_rows: int = 1,
        max_rows: int = 3,
        suggested_max_column_width: int = 30,
        show_meta: FilterOrBool = True,
        extra_filter: FilterOrBool = True,
        z_index: int = 10 ** 8,
    ) -> None:

        show_meta = to_filter(show_meta)
        extra_filter = to_filter(extra_filter)

        # Display filter: show when there are completions but not at the point
        # we are returning the input.
        full_filter = has_completions & ~is_done & extra_filter

        @Condition
        def any_completion_has_meta() -> bool:
            complete_state = get_app().current_buffer.complete_state
            return complete_state is not None and any(
                c.display_meta for c in complete_state.completions
            )

        # Create child windows.
        # NOTE: We don't set style='class:completion-menu' to the
        #       `MultiColumnCompletionMenuControl`, because this is used in a
        #       Float that is made transparent, and the size of the control
        #       doesn't always correspond exactly with the size of the
        #       generated content.
        completions_window = ConditionalContainer(
            content=Window(
                content=MultiColumnCompletionMenuControl(
                    min_rows=min_rows,
                    max_rows=max_rows,
                    suggested_max_column_width=suggested_max_column_width,
                ),
                width=Dimension(min=8),
                height=Dimension(min=1),
            ),
            filter=full_filter,
        )

        meta_window = ConditionalContainer(
            content=Window(content=_SelectedCompletionMetaControl()),
            filter=show_meta & full_filter & any_completion_has_meta,
        )

        # Initialise split.
        super().__init__([completions_window, meta_window], z_index=z_index)


class _SelectedCompletionMetaControl(UIControl):
    """
    Control that shows the meta information of the selected completion.
    """

    def preferred_width(self, max_available_width: int) -> Optional[int]:
        """
        Report the width of the longest meta text as the preferred width of this control.

        It could be that we use less width, but this way, we're sure that the
        layout doesn't change when we select another completion (E.g. that
        completions are suddenly shown in more or fewer columns.)
        """
        app = get_app()
        if app.current_buffer.complete_state:
            state = app.current_buffer.complete_state
            return 2 + max(get_cwidth(c.display_meta_text) for c in state.completions)
        else:
            return 0

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: Optional[GetLinePrefixCallable],
    ) -> Optional[int]:
        return 1

    def create_content(self, width: int, height: int) -> UIContent:
        fragments = self._get_text_fragments()

        def get_line(i: int) -> StyleAndTextTuples:
            return fragments

        return UIContent(get_line=get_line, line_count=1 if fragments else 0)

    def _get_text_fragments(self) -> StyleAndTextTuples:
        style = "class:completion-menu.multi-column-meta"
        state = get_app().current_buffer.complete_state

        if (
            state
            and state.current_completion
            and state.current_completion.display_meta_text
        ):
            return to_formatted_text(
                cast(StyleAndTextTuples, [("", " ")])
                + state.current_completion.display_meta
                + [("", " ")],
                style=style,
            )

        return []
