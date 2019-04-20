"""
Data structures for the selection.
"""
__all__ = [
    'SelectionType',
    'PasteMode',
    'SelectionState',
]


class SelectionType:
    """
    Type of selection.
    """
    #: Characters. (Visual in Vi.)
    CHARACTERS = 'CHARACTERS'

    #: Whole lines. (Visual-Line in Vi.)
    LINES = 'LINES'

    #: A block selection. (Visual-Block in Vi.)
    BLOCK = 'BLOCK'


class PasteMode:
    EMACS = 'EMACS'  # Yank like emacs.
    VI_AFTER = 'VI_AFTER'  # When pressing 'p' in Vi.
    VI_BEFORE = 'VI_BEFORE'  # When pressing 'P' in Vi.


class SelectionState:
    """
    State of the current selection.

    :param original_cursor_position: int
    :param type: :class:`~.SelectionType`
    """
    def __init__(self, original_cursor_position=0, type=SelectionType.CHARACTERS):
        self.original_cursor_position = original_cursor_position
        self.type = type

    def __repr__(self):
        return '{}(original_cursor_position={!r}, type={!r})'.format(
            self.__class__.__name__,
            self.original_cursor_position, self.type)
