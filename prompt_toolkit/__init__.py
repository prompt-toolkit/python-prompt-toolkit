"""
Pure Python alternative to readline.

Still experimental and incomplete. It should be able to handle RAW vt100 input
sequences for a command line and construct a command line with autocompletion
there.
"""
from __future__ import unicode_literals
import sys
import codecs
import six

from .code import Code
from .inputstream import InputStream
from .inputstream_handler import InputStreamHandler
from .line import Line, Exit, ReturnInput, Abort
from .prompt import Prompt
from .renderer import Renderer
from .utils import raw_mode, call_on_sigwinch


class CommandLine(object):
    """
    Wrapper around all the other classes, tying everything together.
    """
    #: The `Line` class which implements the text manipulation.
    line_cls = Line

    #: A `Code` class which implements the interpretation of the text input.
    #: It tokenizes/parses the input text.
    code_cls = Code

    #: `Prompt` class for the layout of the prompt. (and the help text.)
    prompt_cls = Prompt

    #: `InputStream` class for the parser of the input
    #: (Normally, you don't override this one.)
    inputstream_cls = InputStream

    #: `InputStreamHandler` class for the keybindings.
    inputstream_handler_cls = InputStreamHandler

    #: `Renderer` class.
    renderer_cls = Renderer

    #: `pygments.style.Style` class for the syntax highlighting.
    style_cls = None

    def __init__(self, stdin=None, stdout=None):
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout

        # In case of Python2, sys.stdin.read() returns bytes instead of unicode
        # characters. By wrapping it in getreader('utf-8'), we make sure to
        # read valid unicode characters.
        if not six.PY3:
            self.stdin = codecs.getreader('utf-8')(sys.stdin)

        self._renderer = self.renderer_cls(self.stdout, style=self.style_cls)
        self._line = self.line_cls(renderer=self._renderer,
                        code_cls=self.code_cls, prompt_cls=self.prompt_cls)
        self._inputstream_handler = self.inputstream_handler_cls(self._line)

    def read_input(self):
        """
        Read input from command line.
        This can raise `Exit`, when the user presses Ctrl-D.
        """
        # create input stream
        stream = self.inputstream_cls(self._inputstream_handler, stdout=self.stdout)

        def render():
            self._renderer.render(self._line.get_render_context())

        with raw_mode(self.stdin):
            render()

            with call_on_sigwinch(render):
                while True:
                    c = self.stdin.read(1)

                    try:
                        # Feed one character at a time. Feeding can cause the
                        # `Line` object to raise Exit/Abort/ReturnInput
                        stream.feed(c)

                    except Exit as e:
                        self._renderer.render(e.render_context)
                        raise

                    except Abort as abort:
                        self._renderer.render(abort.render_context)
                        stream = InputStream(self._inputstream_handler) # XXX: should we make the stream reusable???

                    except ReturnInput as input:
                        self._renderer.render(input.render_context)
                        return input.document

                    # TODO: completions should be 'rendered' as well through an exception.

                    # Now render the current prompt to the output.
                    # TODO: unless `select` tells us that there's another character to feed.
                    render()
