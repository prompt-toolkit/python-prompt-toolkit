Python Prompt Toolkit
=====================

(Work in progress. Many things work, but APIs can change.)


``prompt_toolkit`` is a Library for building powerful interactive command lines
in Python. It ships with a nice Python shell built on top of the library.

``prompt_toolkit`` can be a replacement for ``readline``. It's Pure Python, and has
some advanced features:

- Syntax highlighting of the input while typing. (For instance, with a Pygments lexer.)
- Multiline input editing
- Advanced code completion
- Both Emacs and Vi keybindings (Similar to readline), including
- Reverse and forward incremental search
- Both Python 2.7 and Python 3
- Works well with Unicode double width characters. (Chinese input.)


Installation
------------

::

    pip install prompt-toolkit


The Python repl
---------------

Run ``ptpython`` to get an interactive Python prompt with syntaxt highlighting,
code completion, etc...

.. image :: docs/images/ptpython-screenshot.png

If you prefer to have Vi keybindings (which currently are more completely
implemented than the Emacs bindings), run ``ptpython --vi``.

If you want to embed the repl inside your application at one point, do:

.. code:: python

    from prompt_toolkit.contrib.repl import embed
    embed(globals(), locals(), vi_mode=False, history_filename=None)


Multiline editing
*****************

Usually, multiline editing mode will automatically turn on when you press enter
after a colon, however you can always turn it on by pressing F7.

To execute the input in multiline mode, you can either press ``Alt+Enter``, or
``Esc`` followed by ``Enter``. (If you want the first to work in the OS X
terminal, you have to check the "Use option as meta key" checkbox in your
terminal settings.)


Using as a library
------------------

This is a library which allows you to build highly customizable input prompts.
Every step (from key bindings, to line behaviour until the renderer can be
customized.)

The simplest example looks like this:

.. code:: python

    from prompt_toolkit import CommandLine
    from prompt_toolkit.line import Exit

    def main():
        # Create CommandLine instance
        cli = CommandLine()

        try:
            while True:
                code_obj = cli.read_input()
                print('You said: ' + code_obj.text)

        except Exit: # Quit on Ctrl-D keypress
            return

    if __name__ == '__main__':
        main()
