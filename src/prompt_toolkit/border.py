"""Defines borders."""


class SquareBorder:
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


class DoubleBorder:
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
