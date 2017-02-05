"""
Abstraction of CLI Input.
"""
from __future__ import unicode_literals

from abc import ABCMeta, abstractmethod, abstractproperty
from six import with_metaclass


__all__ = (
    'Input',
)


class Input(with_metaclass(ABCMeta, object)):
    """
    Abstraction for any input.

    An instance of this class can be given to the constructor of a
    :class:`~prompt_toolkit.application.Application` and will also be
    passed to the :class:`~prompt_toolkit.eventloop.base.EventLoop`.
    """
    @abstractmethod
    def fileno(self):
        """
        Fileno for putting this in an event loop.
        """

    @abstractmethod
    def read_keys(self):
        """
        Return a list of Key objects which are read/parsed from the input.
        """

    def flush(self):
        " The event loop can call this when the input has to be flushed. "
        pass

    @abstractproperty
    def closed(self):
        " Should be true when the input stream is closed. "
        return False

    @abstractmethod
    def raw_mode(self):
        """
        Context manager that turns the input into raw mode.
        """

    @abstractmethod
    def cooked_mode(self):
        """
        Context manager that turns the input into cooked mode.
        """

    def close(self):
        " Close input. "
        pass
