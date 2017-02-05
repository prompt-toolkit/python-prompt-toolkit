from __future__ import unicode_literals
from .containers import Container
from .controls import UIControl
from .utils import find_all_controls

__all__ = (
    'Focus',
)


class Focus(object):
    """
    Keep track of which `UIControl` currently has the focus.
    """
    def __init__(self, layout, focussed_control=None):
        assert isinstance(layout, Container)
        assert focussed_control is None or isinstance(focussed_control, UIControl)

        if focussed_control is None:
            focussed_control = next(find_all_controls(layout))

        self.layout = layout
        self._stack = [focussed_control]

    @property
    def focussed_control(self):
        """
        Get the `UIControl` to currently has the  focus.
        """
        return self._stack[-1]

    @focussed_control.setter
    def focussed_control(self, control):
        """
        Set the `UIControl` to receive the focus.
        """
        assert isinstance(control, UIControl)
        assert control in list(find_all_controls(self.layout))

        if control != self.focussed_control:
            self._stack.append(control)

    @property
    def previous_focussed_control(self):
        """
        Get the `UIControl` to previously had the focus.
        """
        try:
            return self._stack[-2]
        except IndexError:
            return self._stack[-1]

    def focus_previous(self):  # XXX: rename to 'pop()'
        """
        Give the focus to the previously focussed control.
        """
        if len(self._stack) > 1:
            self._stack = self._stack[:-1]
