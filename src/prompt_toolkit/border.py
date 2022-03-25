"""Defines borders."""

from abc import ABCMeta


class Border(metaclass=ABCMeta):
    """Base border type."""

    TOP_LEFT: str
    TOP_SPLIT: str
    TOP_RIGHT: str
    HORIZONTAL: str
    VERTICAL: str
    LEFT_SPLIT: str
    RIGHT_SPLIT: str
    CROSS: str
    BOTTOM_LEFT: str
    BOTTOM_SPLIT: str
    BOTTOM_RIGHT: str


class SquareBorder(Border):
    """Square thin border."""

    TOP_LEFT = "┌"
    TOP_SPLIT = "┬"
    TOP_RIGHT = "┐"
    HORIZONTAL = "─"
    VERTICAL = "│"
    LEFT_SPLIT = "├"
    RIGHT_SPLIT = "┤"
    CROSS = "┼"
    BOTTOM_LEFT = "└"
    BOTTOM_SPLIT = "┴"
    BOTTOM_RIGHT = "┘"


class DoubleBorder(Border):
    """Box drawing characters with double lines."""

    TOP_LEFT = "╔"
    TOP_RIGHT = "╗"
    VERTICAL = "║"
    INNER_VERTICAL = "║"
    HORIZONTAL = "═"
    INNER_HORIZONTAL = "═"
    BOTTOM_LEFT = "╚"
    BOTTOM_RIGHT = "╝"
    SPLIT_LEFT = "╠"
    SPLIT_RIGHT = "╣"
    CROSS = "╬"
