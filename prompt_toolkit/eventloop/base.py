from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from six import with_metaclass

__all__ = (
    'EventLoop',
    'INPUT_TIMEOUT',
)


#: When to trigger the `onInputTimeout` event.
INPUT_TIMEOUT = .5


class EventLoop(with_metaclass(ABCMeta, object)):
    """
    Eventloop interface.
    """
    def run(self, callbacks):
        """
        Run the eventloop until stop() is called. Report all
        input/timeout/terminal-resize events to the callbacks.

        :param callbacks: EventLoopCallback instance.
        """
        raise NotImplementedError

    def run_as_coroutine(self, callbacks):
        """
        Similar to `run`, but this is a coroutine. (For asyncio integration.)
        """
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        """
        Stop the `loop` call. (Normally called by the command line interface,
        when a result is available, or Abort/Quit has been called.)
        """

    @abstractmethod
    def close(self):
        """
        Clean up of resources. Eventloop cannot be reused a second time after
        this call.
        """

    @abstractmethod
    def run_in_executor(self, callback):
        """
        Run a long running function in a background thread.  (This is
        recommended for code that could block the `read_input` event loop.)
        Similar to Twisted's ``deferToThread``.
        """

    @abstractmethod
    def call_from_executor(self, callback):
        """
        Call this function in the main event loop. Similar to Twisted's
        ``callFromThread``.
        """
