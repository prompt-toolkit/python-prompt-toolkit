from __future__ import unicode_literals, absolute_import
from .base import EventLoop, INPUT_TIMEOUT
from .posix_utils import PosixStdinReader
from ..terminal.vt100_input import InputStream

import gtk, gobject
import threading

__all__ = (
    'GtkEventLoop',
)


class GtkEventLoop(EventLoop):
    """
    Adaptor to run run prompt-toolkit on the GTK event loop.
    """
    def run(self, stdin, callbacks):
        stdin_reader = PosixStdinReader(stdin)
        inputstream = InputStream(callbacks.feed_key)

        timeout = [None]  # Nonlocal

        def timeout_received():
            # Flush all pending keys on a timeout and redraw. (This is
            # most important to flush the vt100 escape key early when
            # nothing else follows.)
            inputstream.flush()
            callbacks.redraw()

            # Fire input timeout event.
            callbacks.input_timeout()  # XXX: remove this line.
            timeout[0] = None

        def input_ready(*a, **kw):
            # Cancel last timeout.
            if timeout[0]:
                gobject.source_remove(timeout[0])
                timeout[0] = None

            data = stdin_reader.read()
            inputstream.feed(data)
            callbacks.redraw()

            # Set timeout.
            timeout[0] = gobject.timeout_add(int(1000 * INPUT_TIMEOUT), timeout_received)

            return True

        gobject.io_add_watch(stdin, gobject.IO_IN, input_ready)
        gtk.main()

    def stop(self):
        gtk.main_quit()

    def run_in_executor(self, callback):
        """
        Run a long running function in a background thread.
        (This is recommended for code that could block the event loop.)
        Similar to Twisted's ``deferToThread``.
        """
        # Wait until the main thread is idle for an instant before starting the
        # executor. (Like in eventloop/posix.py, we start the executor using
        # `call_from_executor`.)
        def start_executor():
            threading.Thread(target=callback).start()
        self.call_from_executor(start_executor)

    def call_from_executor(self, callback):
        gobject.idle_add(callback)

    def close(self):
        pass
