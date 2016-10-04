from __future__ import unicode_literals
import datetime
import os
import random
import signal
import threading

from prompt_toolkit.terminal.vt100_input import InputStream
from prompt_toolkit.utils import DummyContext, in_main_thread
from prompt_toolkit.input import Input
from .base import EventLoop, INPUT_TIMEOUT
from .callbacks import EventLoopCallbacks
from .inputhook import InputHookContext
from .posix_utils import PosixStdinReader
from .utils import TimeIt
from .select import select_fds

__all__ = (
    'PosixEventLoop',
)

_now = datetime.datetime.now


class PosixEventLoop(EventLoop):
    """
    Event loop for posix systems (Linux, Mac os X).
    """
    def __init__(self, inputhook=None):
        assert inputhook is None or callable(inputhook)

        self.running = False
        self.closed = False
        self._running = False
        self._callbacks = None

        self._calls_from_executor = []
        self._read_fds = {} # Maps fd to handler.

        # Create a pipe for inter thread communication.
        self._schedule_pipe = os.pipe()
        
        # import on demand
        import fcntl
        fcntl.fcntl(self._schedule_pipe[0], fcntl.F_SETFL, os.O_NONBLOCK)

        # Create inputhook context.
        self._inputhook_context = InputHookContext(inputhook) if inputhook else None

    def run(self, stdin, callbacks):
        """
        The input 'event loop'.
        """
        assert isinstance(stdin, Input)
        assert isinstance(callbacks, EventLoopCallbacks)
        assert not self._running

        if self.closed:
            raise Exception('Event loop already closed.')

        self._running = True
        self._callbacks = callbacks

        inputstream = InputStream(callbacks.feed_key)
        current_timeout = [INPUT_TIMEOUT]  # Nonlocal

        # Create reader class.
        stdin_reader = PosixStdinReader(stdin.fileno())

        # Only attach SIGWINCH signal handler in main thread.
        # (It's not possible to attach signal handlers in other threads. In
        # that case we should rely on a the main thread to call this manually
        # instead.)
        if in_main_thread():
            ctx = call_on_sigwinch(self.received_winch)
        else:
            ctx = DummyContext()

        def read_from_stdin():
            " Read user input. "
            # Feed input text.
            data = stdin_reader.read()
            inputstream.feed(data)

            # Set timeout again.
            current_timeout[0] = INPUT_TIMEOUT

            # Quit when the input stream was closed.
            if stdin_reader.closed:
                self.stop()

        self.add_reader(stdin, read_from_stdin)
        self.add_reader(self._schedule_pipe[0], None)

        with ctx:
            while self._running:
                # Call inputhook.
                with TimeIt() as inputhook_timer:
                    if self._inputhook_context:
                        def ready(wait):
                            " True when there is input ready. The inputhook should return control. "
                            return self._ready_for_reading(current_timeout[0] if wait else 0) != []
                        self._inputhook_context.call_inputhook(ready)

                # Calculate remaining timeout. (The inputhook consumed some of the time.)
                if current_timeout[0] is None:
                    remaining_timeout = None
                else:
                    remaining_timeout = max(0, current_timeout[0] - inputhook_timer.duration)

                # Wait until input is ready.
                fds = self._ready_for_reading(remaining_timeout)

                # When any of the FDs are ready. Call the appropriate callback.
                if fds:
                    # Create lists of high/low priority tasks. The main reason
                    # for this is to allow painting the UI to happen as soon as
                    # possible, but when there are many events happening, we
                    # don't want to call the UI renderer 1000x per second. If
                    # the eventloop is completely saturated with many CPU
                    # intensive tasks (like processing input/output), we say
                    # that drawing the UI can be postponed a little, to make
                    # CPU available. This will be a low priority task in that
                    # case.
                    tasks = []
                    low_priority_tasks = []
                    now = _now()

                    for fd in fds:
                        # For the 'call_from_executor' fd, put each pending
                        # item on either the high or low priority queue.
                        if fd == self._schedule_pipe[0]:
                            for c, max_postpone_until in self._calls_from_executor:
                                if max_postpone_until is None or max_postpone_until < now:
                                    tasks.append(c)
                                else:
                                    low_priority_tasks.append((c, max_postpone_until))
                            self._calls_from_executor = []

                            # Flush all the pipe content.
                            os.read(self._schedule_pipe[0], 1024)
                        else:
                            handler = self._read_fds.get(fd)
                            if handler:
                                tasks.append(handler)

                    # Handle everything in random order. (To avoid starvation.)
                    random.shuffle(tasks)
                    random.shuffle(low_priority_tasks)

                    # When there are high priority tasks, run all these.
                    # Schedule low priority tasks for the next iteration.
                    if tasks:
                        for t in tasks:
                            t()

                        # Postpone low priority tasks.
                        for t, max_postpone_until in low_priority_tasks:
                            self.call_from_executor(t, _max_postpone_until=max_postpone_until)
                    else:
                        # Currently there are only low priority tasks -> run them right now.
                        for t, _ in low_priority_tasks:
                            t()

                else:
                    # Flush all pending keys on a timeout. (This is most
                    # important to flush the vt100 'Escape' key early when
                    # nothing else follows.)
                    inputstream.flush()

                    # Fire input timeout event.
                    callbacks.input_timeout()
                    current_timeout[0] = None

        self.remove_reader(stdin)
        self.remove_reader(self._schedule_pipe[0])

        self._callbacks = None

    def _ready_for_reading(self, timeout=None):
        """
        Return the file descriptors that are ready for reading.
        """
        read_fds = list(self._read_fds.keys())
        fds = select_fds(read_fds, timeout)
        return fds

    def received_winch(self):
        """
        Notify the event loop that SIGWINCH has been received
        """
        # Process signal asynchronously, because this handler can write to the
        # output, and doing this inside the signal handler causes easily
        # reentrant calls, giving runtime errors..

        # Furthur, this has to be thread safe. When the CommandLineInterface
        # runs not in the main thread, this function still has to be called
        # from the main thread. (The only place where we can install signal
        # handlers.)
        def process_winch():
            if self._callbacks:
                self._callbacks.terminal_size_changed()

        self.call_from_executor(process_winch)

    def run_in_executor(self, callback):
        """
        Run a long running function in a background thread.
        (This is recommended for code that could block the event loop.)
        Similar to Twisted's ``deferToThread``.
        """
        # Wait until the main thread is idle.
        # We start the thread by using `call_from_executor`. The event loop
        # favours processing input over `calls_from_executor`, so the thread
        # will not start until there is no more input to process and the main
        # thread becomes idle for an instant. This is good, because Python
        # threading favours CPU over I/O -- an autocompletion thread in the
        # background would cause a significantly slow down of the main thread.
        # It is mostly noticable when pasting large portions of text while
        # having real time autocompletion while typing on.
        def start_executor():
            threading.Thread(target=callback).start()
        self.call_from_executor(start_executor)

    def call_from_executor(self, callback, _max_postpone_until=None):
        """
        Call this function in the main event loop.
        Similar to Twisted's ``callFromThread``.

        :param _max_postpone_until: `None` or `datetime` instance. For interal
            use. If the eventloop is saturated, consider this task to be low
            priority and postpone maximum until this timestamp. (For instance,
            repaint is done using low priority.)
        """
        self._calls_from_executor.append((callback, _max_postpone_until))

        if self._schedule_pipe:
            os.write(self._schedule_pipe[1], b'x')

    def stop(self):
        """
        Stop the event loop.
        """
        self._running = False

    def close(self):
        self.closed = True

        # Close pipes.
        schedule_pipe = self._schedule_pipe
        self._schedule_pipe = None

        if schedule_pipe:
            os.close(schedule_pipe[0])
            os.close(schedule_pipe[1])

        if self._inputhook_context:
            self._inputhook_context.close()

    def add_reader(self, fd, callback):
        " Add read file descriptor to the event loop. "
        self._read_fds[fd] = callback

    def remove_reader(self, fd):
        " Remove read file descriptor from the event loop. "
        if fd in self._read_fds:
            del self._read_fds[fd]


class call_on_sigwinch(object):
    """
    Context manager which Installs a SIGWINCH callback.
    (This signal occurs when the terminal size changes.)
    """
    def __init__(self, callback):
        self.callback = callback
        self.previous_callback = None

    def __enter__(self):
        self.previous_callback = signal.signal(signal.SIGWINCH, lambda *a: self.callback())

    def __exit__(self, *a, **kw):
        if self.previous_callback is None:
            # Normally, `signal.signal` should never return `None`.
            # For some reason it happens here:
            # https://github.com/jonathanslenders/python-prompt-toolkit/pull/174
            signal.signal(signal.SIGWINCH, 0)
        else:
            signal.signal(signal.SIGWINCH, self.previous_callback)
