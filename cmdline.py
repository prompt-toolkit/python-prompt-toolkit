"""
Pure Python alternative to readline.

Still experimental and incomplete. It should be able to handle RAW vt100 input
sequences for a command line and construct a command line with autocompletion
there.
"""

import os
import sys


__all__ = ('InputStream', 'CommandLineHandler',)


class InputStream:
    """
    Parser for VT100 input stream.
    Feed the data through the ``feed`` method and the correct callbacks of the
    attached interfaces will be called.

    ::

        i = InputStream()
        h = CommandLineHandler()
        i.attach(h)
        i.feed('data\x01...')
    """
    # Lookup table of ANSI escape sequences for a VT100 terminal
    handler = {
        '\x01': 'ctrl_a', # Control-A (home)
        '\x02': 'ctrl_b', # Control-B (emacs cursor left)
        '\x03': 'ctrl_c', # Control-C (interrupt)
        '\x04': 'ctrl_d', # Control-D (exit)
        '\x05': 'ctrl_e', # Contrel-E (end)
        '\x06': 'ctrl_f', # Control-F (cursor forward)
        '\x0b': 'ctrl_k', # Control-K (delete until end of line)
        '\x0c': 'ctrl_l', # Control-L (clear)
        '\x0e': 'ctrl_n', # Control-N 14 (history forward)
        '\x10': 'ctrl_p', # Control-P 16 (history back)
        '\x12': 'ctrl_r', # Control-R (18)
        '\r': 'enter', # Enter
        '\n': 'enter', # Enter
        '\t': 'tab', # Tab
        '\x7f': 'backspace', # (127) Backspace
        '\x1b[A': 'cursor_up',
        '\x1b[B': 'cursor_down',
        '\x1b[C': 'cursor_right',
        '\x1b[D': 'cursor_left',
        '\x1b[H': 'home',
        '\x1b[F': 'end',
        '\x1b[3~': 'delete',
        '\x1b[1~': 'home', # tmux
        '\x1b[7~': 'home', # xrvt
        '\x1b[4~': 'end', # tmux
        '\x1b[8~': 'end', # xrvt
    }

    def __init__(self):
        self._input_parser = self._input_parser_generator()
        self._input_parser.send(None)
        self._attached_handlers = []

    def _input_parser_generator(self):
        """
        State machine for the input parser.
        """
        while True:
            options = self.handler
            prefix = ''

            while True:
                c = yield

                # When we have a match -> call handler
                if c in options:
                    self._call_handler(options[c])
                    break # Reset. Go back to outer loop

                # When the first character matches -> pop first letters in options dict
                elif c in [ k[0] for k in options.keys() ]:
                    options = { k[1:]: v for k, v in options.items() if k[0] == c }
                    prefix += c

                # An 'invalid' escape sequence is a literal escape.
                elif prefix and prefix[0] == '\x1b':
                    self._call_handler('escape')
                    break # Reset. Go back to outer loop
                # Handle letter
                else:
                    self._call_handler('insert_data', prefix + c)
                    break # Reset. Go back to outer loop

    def _call_handler(self, name, *a):
        """
        Call appropriate method for all the attach handlers.
        """
        for i in self._attached_handlers:
            method = getattr(i, name, None)
            if method:
                method(*a)

    def feed(self, data):
        """
        Feed the input stream.
        """
        assert isinstance(data, str)

        for c in data:
            self._input_parser.send(c)

    def attach(self, cli):
        """
        Attach CommandLineHandler.
        """
        self._attached_handlers.append(cli)


class CommandLineHandler:
    """
    Interface with all callbacks for events coming from the
    :class:`InputStream`.
    """
    def __init__(self, ):
        self.reset()

    def reset(self):
        self.text = ''
        self.cursor_position = 0

    def home(self):
        self.cursor_position = 0

    def end(self):
        self.cursor_position = len(self.text)

    def cursor_left(self):
        if self.cursor_position > 0:
            self.cursor_position -= 1

    def cursor_right(self):
        if self.cursor_position <= len(self.text):
            self.cursor_position += 1

    def backspace(self):
        if self.cursor_position > 0:
            self.text = self.text[:self.cursor_position - 1] + self.text[self.cursor_position:]
            self.cursor_position -= 1

    def exit(self):
        os.exit()

    def insert_data(self, data):
        """ Insert data at cursor position.  """
        self.text = self.text[:self.cursor_position] + data + self.text[self.cursor_position:]
        self.cursor_position += len(data)

    def ctrl_c(self):
        raise KeyboardInterrupt

    def ctrl_l(self):
        pass

    def history_forward(self):
        pass

    def history_back(self):
        pass

    def ctrl_r(self):
        # TODO: Implement reverse search.
        pass

    def enter(self):
        pass

    # Add emacs shortcuts for navigation
    def ctrl_a(self):
        self.home()

    def ctrl_b(self):
        self.cursor_right()

    def ctrl_e(self):
        self.end()

    def ctrl_k(self):
        pass # TODO: delete until end.


class Renderer:
    def render(self, handler):
        out = []; write = out.append

        write('\r') # Cursor to left margin
        write('\x1b[K') # Erase until the end of line
        write(handler.prompt)
        write(handler.text)

        # Position cursor position backward
        backward_count = len(handler.text) - handler.cursor_position
        if backward_count:
            write('\x1b[%iD' % backward_count)

        return ''.join(out)


class CommandLine(CommandLineHandler):
    """
    Wrapper around the input parser, handler and renderer to get a nice command
    line interface. Example usage:

    ::

        cli = CommandLine()
        tty.setraw(sys.stdin)
        cli.cmdloop()
    """
    renderer_cls = Renderer

    def __init__(self, stdin=None, stdout=None):
        super().__init__()
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout

        self._stream = InputStream()
        self._stream.attach(self)
        self._renderer = self.renderer_cls()

    @property
    def prompt(self):
        return '> '

    def ctrl_l(self):
        self.stdout.write('\x1b[2J\x1b[0;0H') # Clear and go to 0,0

    def enter(self):
        self.handle_command(self.text)
        self.reset()

    def ctrl_c(self):
        self.stdout.write('\r\n')
        self.reset()

    def handle_command(self, command):
        """
        Override this command for handling of commands.
        """
        raise NotImplementedError
        #self.stdout.write('\r\nYou said: %r' % command + '\r\n')

    def _render(self):
        sys.stdout.write(self._renderer.render(self))
        sys.stdout.flush()

    def feed_data(self, data):
        """
        Feed input data to the command line.
        """
        self._stream.feed(data)
        self._render()

    def cmdloop(self):
        self._render()

        while True:
            c = self.stdin.read(1)
            self.feed_data(c)



if __name__ == '__main__':
    import tty
    cli = CommandLine()
    tty.setraw(sys.stdin)
    cli.cmdloop()
