"""
Readline compatibility interface.
Implements the 'readline' Python module in pure Python.

This is also an alternative to pyrepl.readline.
"""
from __future__ import unicode_literals

from prompt_toolkit.interface import CommandLineInterface


class _ReadlineWrapper(object):
    def __init__(self):
        self._cli = CommandLineInterface()

        self._readline_completer = None
        self._startup_hook = None

    def add_history(self, line):
        """
        add_history(string) -> None
        add a line to the history buffer
        """
        self._cli.buffers['default'].history.append(line)

    def clear_history(self):
        """
        clear_history() -> None
        Clear the current readline history.
        """
        del self._cli.buffers['default'].history[:]

    def get_begidx(self):
        """
        get_begidx() -> int
        get the beginning index of the readline tab-completion scope
        """
        # TODO

    def get_completer(self):
        """
        get_completer() -> function
        Returns current completer function.
        """
        return self._readline_completer

    def get_completer_delims(self):
        """
        get_completer_delims() -> string
        get the readline word delimiters for tab-completion
        """
        # TODO

    def get_completion_type(self):
         """
         get_completion_type() -> int
         Get the type of completion being attempted.
         """
         # TODO

    def get_current_history_length(self):
        """
        get_current_history_length() -> integer
        return the current (not the maximum) length of history.
        """
        return len(self._cli.buffers['default'].history)  # XXX: not the same as 'get_history_length'!!

    def get_endidx(self):
        """
        get_endidx() -> int
        get the ending index of the readline tab-completion scope
        """

    def get_history_item(self, index):
        """
        get_history_item() -> string
        return the current contents of history item at index.
        """
        h = self._cli.buffers['default'].history
        if 1 <= index <= len(h):
            return h[index - 1]
        else:
            return None  # blame readline.c for not raising

    def get_history_length(self):
        """
        get_history_length() -> int
        return the maximum number of items that will be written to\nthe history file.
        """
        return len(self._cli.buffers['default'].history)

    def get_line_buffer(self):
        """
        get_line_buffer() -> string
        return the current contents of the line buffer.
        """
        # TODO

    def insert_text(self, text):
        """
        insert_text(string) -> None
        Insert text into the command line.
        """
        return self._cli.buffers['default'].insert_text(text)

    def parse_and_bind(self):
        """
        parse_and_bind(string) -> None
        Parse and execute single line of a readline init file.
        """
        raise NotImplementedError

    def read_history_file(self, filename='~/.history'):
        """
        read_history_file([filename]) -> None
        Load a readline history file.\nThe default filename is ~/.history.
        """
        # TODO

    def read_init_file(self):
        """
        read_init_file([filename]) -> None
        Parse a readline initialization file.\nThe default filename is the last filename used.
        """

    def redisplay(self):
        """
        redisplay() -> None
        Change what's displayed on the screen to reflect the current\ncontents of the line buffer.
        """
        self._cli.request_redraw()

    def remove_history_item(self, index):
        """
        remove_history_item(pos) -> None
        remove history item given by its position
        """
        h = self._cli.buffers['default'].history
        if 1 <= index <= len(h):
            del h[index - 1]
        else:
            raise ValueError("No history item at position %d" % index)
            # blame readline.c for raising ValueError

    def replace_history_item(self, index, line):
        """
        replace_history_item(pos, line) -> None
        replaces history item given by its position with contents of line
        """
        h = self._cli.buffers['default'].history
        if 1 <= index <= len(h):
            h[index - 1] = line
        else:
            raise ValueError("No history item at position %d" % index)
            # blame readline.c for raising ValueError

    def set_completer(self, function=None):
        """
        set_completer([function]) -> None

        Set or remove the completer function.
        The function is called as function(text, state),
        for state in 0, 1, 2, ..., until it returns a non-string.
        It should return the next possible completion starting with 'text'."
        """
        self._readline_completer = function

    def set_completer_delims(self, string):
        """
        set_completer_delims(string) -> None
        set the readline word delimiters for tab-completion
        """
        # TODO

    def set_completion_display_matches_hook(self, function):
        """
        set_completion_display_matches_hook([function]) -> None

        Set or remove the completion display function.
        The function is called as
            function(substitution, [matches], longest_match_length)
        once each time matches need to be displayed.'
        """

    def set_history_length(self, length):
        """
        set_history_length(length) -> None

        set the maximal number of items which will be written to
        the history file. A negative length is used to inhibit
        history truncation.'
        """

    def set_pre_input_hook(self,):
        """
        set_pre_input_hook([function]) -> None

        Set or remove the pre_input_hook function.
        The function is called with no arguments after the first prompt
        has been printed and just before readline starts reading input
        characters.'
        """

    def set_startup_hook(self, function):
        """
        set_startup_hook([function]) -> None

        Set or remove the startup_hook function.
        The function is called with no arguments just
        before readline prints the first prompt.'
        """
        self._startup_hook = function

    def write_history_file(self, filename='~/.history'):
        """
        write_history_file([filename]) -> None

        Save a readline history file.
        The default filename is ~/.history.'
        """
        # TODO


# Public API
_wrapper = _ReadlineWrapper()

add_history = _wrapper.add_history
clear_history = _wrapper.clear_history
get_begidx = _wrapper.get_begidx
get_completer = _wrapper.get_completer
get_completer_delims = _wrapper.get_completer_delims
get_current_history_length = _wrapper.get_current_history_length
get_endidx = _wrapper.get_endidx
get_history_item = _wrapper.get_history_item
get_history_length = _wrapper.get_history_length
get_line_buffer = _wrapper.get_line_buffer
insert_text = _wrapper.insert_text
parse_and_bind = _wrapper.parse_and_bind
read_history_file = _wrapper.read_history_file
remove_history_item = _wrapper.remove_history_item
replace_history_item = _wrapper.replace_history_item
set_completer = _wrapper.set_completer
set_completer_delims = _wrapper.set_completer_delims
set_history_length = _wrapper.set_history_length
set_startup_hook = _wrapper.set_startup_hook
write_history_file = _wrapper.write_history_file
