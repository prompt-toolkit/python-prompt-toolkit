#!/usr/bin/env python
"""
Simple example of a syntax-highlighted HTML input line.
"""
from pygments.lexers import HtmlLexer

from pyline import CommandLine
from pyline.code import Code
from pyline.line import Exit


class HtmlCode(Code):
    lexer_cls = HtmlLexer


class HtmlCommandLine(CommandLine):
    code_cls = HtmlCode


def main():
    # Create CommandLine instance
    cli = HtmlCommandLine()

    try:
        while True:
            # Read one line. (
            html_code_obj = cli.read_input()
            print('You said: ' + html_code_obj.text)

    except Exit: # Quit on Ctrl-D keypress (End-of-file)
        pass

if __name__ == '__main__':
    main()
