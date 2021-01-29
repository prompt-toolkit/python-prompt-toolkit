from collections import defaultdict
from itertools import product
from typing import Callable, DefaultDict, Tuple

from prompt_toolkit.mouse_events import MouseEvent

__all__ = [
    "MouseHandler",
    "MouseHandlers",
]

MouseHandler = Callable[[MouseEvent], None]


class MouseHandlers:
    """
    Two dimensional raster of callbacks for mouse events.
    """

    def __init__(self) -> None:
        def dummy_callback(mouse_event: MouseEvent) -> None:
            """
            :param mouse_event: `MouseEvent` instance.
            """

        # NOTE: Previously, the data structure was a dictionary mapping (x,y)
        # to the handlers. This however would be more inefficient when copying
        # over the mouse handlers of the visible region in the scrollable pane.

        # Map y (row) to x (column) to handlers.
        self.mouse_handlers: DefaultDict[
            int, DefaultDict[int, MouseHandler]
        ] = defaultdict(lambda: defaultdict(lambda: dummy_callback))

    def set_mouse_handler_for_range(
        self,
        x_min: int,
        x_max: int,
        y_min: int,
        y_max: int,
        handler: Callable[[MouseEvent], None],
    ) -> None:
        """
        Set mouse handler for a region.
        """
        for y in range(y_min, y_max):
            row = self.mouse_handlers[y]

            for x in range(x_min, x_max):
                row[x] = handler
