from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING, Any

from .ansi import ANSI
from .base import StyleAndTextTuples

if TYPE_CHECKING:
    from rich.style import StyleType

__all__ = [
    "Rich",
]


class Rich:
    """
    Turn any rich text object from the `rich` library into prompt_toolkit
    formatted text, so that it can be used in a prompt or anywhere else.

    Note that `to_formatted_text` automatically recognizes objects that have a
    `__rich_console__` attribute and will wrap them in a `Rich` instance.
    """

    def __init__(
        self,
        rich_object: Any,
        width: int | None = None,
        style: StyleType | None = None,
    ) -> None:
        self.rich_object = rich_object
        self.width = width
        self.style = style

    def __pt_formatted_text__(self) -> StyleAndTextTuples:
        from rich.console import Console

        file = StringIO()

        console = Console(
            file=file,
            force_terminal=True,
            color_system="truecolor",
            width=self.width,
            style=self.style,
        )
        console.print(self.rich_object, end="")
        ansi = file.getvalue()
        return ANSI(ansi).__pt_formatted_text__()
