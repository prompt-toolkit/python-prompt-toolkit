"""
Utility for printing colored logs.
"""
import datetime
import logging
from typing import Callable, Optional, TextIO, Union

from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout.containers import AnyContainer, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

from .utils import print_container, print_formatted_text

__all__ = ["PromptToolkitLogHandler"]


def default_template(record: logging.LogRecord) -> HTML:
    now = datetime.datetime.now()
    return HTML(
        f"<{record.levelname}>"
        "<time>[{now}]</time> <level>{level:10}</level> <message>{msg}</message>"
        f"</{record.levelname}>"
    ).format(
        now=now.strftime("%m/%d/%y %H:%M:%S"),
        level=record.levelname,
        msg=record.msg,
    )


def default_style() -> Style:
    return Style.from_dict(
        {
            "time": "ansimagenta",
            "warning": "#aa8888",
            "warning level": "reverse",
            "debug": "#888888",
            "error": "ansired",
            "error level": "reverse",
            "info": "#00aa00",
        }
    )


class PromptToolkitLogHandler(logging.StreamHandler):
    """
    Print all logging messages using the given template.

    Usage::

        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            handlers=[PromptToolkitHandler()]
        )
    """
    # NOTE: Previously, I tried using `print_container` instead of
    #       `print_formatted_text`. This doesn't work unfortunately, because
    #       we'd try to create/access an event loop, which causes asyncio to
    #       log new messages. We can't log anything while printing a log
    #       message.

    def __init__(
        self,
        template: Callable[[logging.LogRecord], HTML] = default_template,
        style: Style = default_style(),
        stream: Optional[TextIO] = None,
    ) -> None:
        self.template = template
        self.style = style
        super().__init__(stream=stream)

    def emit(self, record) -> None:
        print_formatted_text(self.template(record), style=self.style, file=self.stream)
