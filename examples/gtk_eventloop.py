"""
Running on top of the GTK event loop.

This example demonstrates that it's possible to read input from stdin, while
there are GTK windows displayed and interactive at the same time.
Prompt-toolkit integrates with the GTK event loop.

One thing worth noting is that the ``get_input`` function is blocking. It
calls ``gtk.main()`` and runs the loop until the command line input was
accepted.  --  TODO: Maybe we want to have a callback interface as well, and
call gtk.main() ourself.

For the fun, we apply Python syntax highlighting to the input.
"""
from __future__ import unicode_literals

from prompt_toolkit.shortcuts import get_input
from prompt_toolkit.eventloop.gtk import GtkEventLoop

from pygments.lexers import PythonLexer

import gtk


def hello_world_window():
    """
    Create a GTK window with one 'Hello world' button.
    """
    # create a new window
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.set_border_width(50)

    # Creates a new button with the label "Hello World".
    button = gtk.Button("Hello World")
    window.add(button)

    # The final step is to display this newly created widget.
    button.show()
    window.show()


def main():
    hello_world_window()

    # Read input from the command line, using the GTK event loop.
    gtk_loop = GtkEventLoop()
    result = get_input('hello>', eventloop=gtk_loop, lexer=PythonLexer)
    print('You said: %s' % result)


if __name__ == '__main__':
    main()
