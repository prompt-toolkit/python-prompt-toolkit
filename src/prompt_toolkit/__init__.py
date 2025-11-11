"""
prompt_toolkit
==============

Author: Jonathan Slenders

Description: prompt_toolkit is a Library for building powerful interactive
             command lines in Python.  It can be a replacement for GNU
             Readline, but it can be much more than that.

See the examples directory to learn about the usage.

Probably, to get started, you might also want to have a look at
`prompt_toolkit.shortcuts.prompt`.
"""

from __future__ import annotations

from typing import Any

from .application import Application
from .formatted_text import ANSI, HTML
from .shortcuts import PromptSession, choice, print_formatted_text, prompt

__version__: str
VERSION: tuple[int, int, int]


def _load_version() -> None:
    """
    Load the package version from importlib.metadata and cache both __version__
    and VERSION in the module globals.
    """
    global __version__, VERSION

    import re
    from importlib import metadata

    # note: this is a bit more lax than the actual pep 440 to allow for a/b/rc/dev without a number
    pep440_pattern = (
        r"^([1-9]\d*!)?(0|[1-9]\d*)(\.(0|[1-9]\d*))*"
        r"((a|b|rc)(0|[1-9]\d*)?)?(\.post(0|[1-9]\d*))?(\.dev(0|[1-9]\d*)?)?$"
    )

    version = metadata.version("prompt_toolkit")
    assert re.fullmatch(pep440_pattern, version)

    # Version string.
    __version__ = version

    # Version tuple.
    parts = [int(v.rstrip("abrc")) for v in version.split(".")]
    VERSION = (parts[0], parts[1], parts[2])


def __getattr__(name: str) -> Any:
    if name in {"__version__", "VERSION"}:
        _load_version()
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(
        {
            *globals().keys(),
            "__version__",
            "VERSION",
        }
    )


__all__ = [
    # Application.
    "Application",
    # Shortcuts.
    "prompt",
    "choice",
    "PromptSession",
    "print_formatted_text",
    # Formatted text.
    "HTML",
    "ANSI",
    # Version info.
    "__version__",
    "VERSION",
]
