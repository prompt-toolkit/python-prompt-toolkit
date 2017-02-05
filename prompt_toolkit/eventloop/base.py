from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from six import with_metaclass, exec_
import textwrap

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
    def run_until_complete(self, future):
        """
        Keep running until this future has been set.
        Return the Future's result, or raise its exception.
        """
        raise NotImplementedError(
            "This eventloop doesn't implement synchronous 'run_until_complete()'.")

    try:
        exec_(textwrap.dedent('''
    async def run_as_coroutine(self, future):
        " Similar to `run`, but this is a coroutine. (For asyncio integration.) "
        raise NotImplementedError(
            "This eventloop doesn't implement 'run_as_coroutine()'.")
    '''), globals(), locals())
    except SyntaxError:
        def run_as_coroutine(self, future):
            """ Similar to `run`, but this is a coroutine. (For asyncio
            integration.) """
            pass

    @abstractmethod
    def close(self):
        """
        Clean up of resources. Eventloop cannot be reused a second time after
        this call.
        """

    @abstractmethod
    def add_reader(self, fd, callback):
        """
        Start watching the file descriptor for read availability and then call
        the callback.
        """

    @abstractmethod
    def remove_reader(self, fd):
        """
        Stop watching the file descriptor for read availability.
        """

    @abstractmethod
    def set_input(self, input, input_ready_callback):
        """
        Tell the eventloop to read from this input object.

        :param input: :class:`~prompt_toolkit.input.Input` object.
        :param input_ready_callback: Called when the input is ready to read.
        """

    @abstractmethod
    def remove_input(self):
        """
        Remove the currently attached `Input`.
        """

    @abstractmethod
    def run_in_executor(self, callback):
        """
        Run a long running function in a background thread. (This is
        recommended for code that could block the event loop.)
        Similar to Twisted's ``deferToThread``.
        """

    @abstractmethod
    def call_from_executor(self, callback, _max_postpone_until=None):
        """
        Call this function in the main event loop. Similar to Twisted's
        ``callFromThread``.

        :param _max_postpone_until: `None` or `time.time` value. For interal
            use. If the eventloop is saturated, consider this task to be low
            priority and postpone maximum until this timestamp. (For instance,
            repaint is done using low priority.)

            Note: In the past, this used to be a datetime.datetime instance,
                  but apparently, executing `time.time` is more efficient: it
                  does fewer system calls. (It doesn't read /etc/localtime.)
        """
