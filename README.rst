pyline
======

(WORK IN PROGRESS)

Library for building interactive command lines in Python.

It could be a replacement for `readline`, but it's more powerful:

- Syntax highlighting of the input while typing. (Usually with a Pygments lexer.)
- Multiline input.
- Advanced code completion.

The Python repl
---------------

Run `./bin/pyline-python-repl` to get an interactive Python prompt with syntaxt
highlighting, code completion, etc...


Example
-------

.. code:: python

    from pyline import CommandLine
    from pyline.line import Exit

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
