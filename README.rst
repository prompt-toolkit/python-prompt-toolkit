Python Prompt Toolkit
=====================

(This is work in progress. Many things work, but APIs can change.)


`prompt_toolkit` is a Library for building interactive command lines in Python.

It could be a replacement for `readline`. It's Pure Python, and has some
advanced features:

- Syntax highlighting of the input while typing. (Usually with a Pygments lexer.)
- Multiline input
- Advanced code completion
- Both Emacs and Vi keybindings (Similar to readline), including
  reverse and forward incremental search
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

If you prefer to have Vi keybindings (which currently are more completely
implemented than the Emacs bindings), run ``ptpython --vi``.


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
