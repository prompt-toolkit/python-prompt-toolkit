Python Prompt Toolkit
=====================

(WORK IN PROGRESS)


`prompt_toolkit` is a Library for building interactive command lines in Python.

It could be a replacement for `readline`. It's Pure Python, and has some
advanced features:

- Syntax highlighting of the input while typing. (Usually with a Pygments lexer.)
- Multiline input
- Advanced code completion
- Both Emacs and Vi keybindings (Similar to readline), including
  reverse and forward incremental search


The Python repl
---------------

Run `./bin/prompt-toolkit-python-repl` to get an interactive Python prompt with
syntaxt highlighting, code completion, etc...


Example
-------

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
