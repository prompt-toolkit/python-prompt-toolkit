from __future__ import unicode_literals
from .containers import Container
from .controls import UIControl
from .containers import Window, to_container

__all__ = (
    'Layout',
)


class Layout(object):
    """
    The layout for a prompt_toolkit
    :class:`~prompt_toolkit.application.Application`.
    This also keeps track of which user control is focussed.

    :param container: The "root" container for the layout.
    :param focussed_control: The `UIControl` to be focused initially.
    """
    def __init__(self, container, focussed_control=None):
        assert focussed_control is None or isinstance(focussed_control, UIControl)

        self.container = to_container(container)
        self._stack = []

        if focussed_control is None:
            self._stack.append(next(self.find_all_controls()))
        else:
            self._stack.append(focussed_control)

    def __repr__(self):
        return 'Layout(%r, focussed_control=%r)' % (
            self.container, self.focussed_control)

    def find_all_controls(self):
        """
        Find all the `UIControl` objects in this layout.
        """
        for item in self.container.walk():
            if isinstance(item, Window):
                yield item.content

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
        assert control in self.find_all_controls()

        if control != self.focussed_control:
            self._stack.append(control)

    @property
    def focussed_window(self):
        " Return the `Window` object that is currently focussed. "
        for item in self.walk():
            if isinstance(item, Window) and item.content == self.focussed_control:
                return item

    @focussed_window.setter
    def focussed_window(self, value):
        " Set the `Window` object to be currently focussed. "
        assert isinstance(value, Window)
        self.focussed_control = value.content

    @property
    def previous_focussed_control(self):
        """
        Get the `UIControl` to previously had the focus.
        """
        try:
            return self._stack[-2]
        except IndexError:
            return self._stack[-1]

    def pop_focus(self):
        """
        Give the focus to the previously focussed control.
        """
        if len(self._stack) > 1:
            self._stack = self._stack[:-1]

    def walk(self):
        """
        Walk through all the layout nodes (and their children) and yield them.
        """
        return self.container.walk()

    def reset(self):
        return self.container.reset()
