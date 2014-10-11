#!/usr/bin/env python
"""
This is an example of "prompt_toolkit.contrib.regular_languages" which
implements a litle calculator.

Type for instance::

    > add 4 4
    > sub 4 4
    > sin 3.14

This example shows how you can define the grammar of a regular language and how
to use variables in this grammar with completers and tokens attached.
"""
from prompt_toolkit import CommandLineInterface
from prompt_toolkit import Exit
from prompt_toolkit.line import Line
from prompt_toolkit.layout.menus import CompletionsMenu

from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.prompt import DefaultPrompt
import math

from pygments.style import Style
from pygments.token import Token

from prompt_toolkit import AbortAction
from prompt_toolkit.contrib.regular_languages.grammar import Variable, Regex, Repeat
from prompt_toolkit.contrib.regular_languages.completion import GrammarCompleter
from prompt_toolkit.contrib.regular_languages.compiler import compile
from prompt_toolkit.contrib.regular_languages.lexer import GrammarLexer
from prompt_toolkit.contrib.completers import WordCompleter


def create_grammar():
    whitespace = Repeat(Regex(r'[ \t]'))  # Note this 'Repeat is a '*'-repeat, not a '+'-repeat.
    required_whitespace = Regex(r'[ \t]+')

    operator_completer = WordCompleter(['add', 'sub', 'div', 'mul'])
    operator_completer2 = WordCompleter(['sqrt', 'log', 'sin', 'ln'])

    return compile(
            # Operators with two arguments.
            (
                whitespace +
                Variable(Regex(r'[a-z]+'), varname='operator', completer=operator_completer, token=Token.Operator) +
                required_whitespace +
                Variable(Regex(r'[0-9.]+'), varname='var1', token=Token.Number) +
                required_whitespace +
                Variable(Regex(r'[0-9.]+'), varname='var2', token=Token.Number) +
                whitespace
            ) |
            # Operators with one argument.
            (
                whitespace +
                Variable(Regex(r'[a-z]+'), varname='operator', completer=operator_completer2, token=Token.Operator) +
                required_whitespace +
                Variable(Regex(r'[0-9.]+'), varname='var1', token=Token.Number) +
                whitespace
            )
    )


class ExampleStyle(Style):
    background_color = None
    styles = {
        Token.Placeholder: "#888888",
        Token.Placeholder.Variable: "#888888",
        Token.Placeholder.Bracket: "bold #ff7777",
        Token.Placeholder.Separator: "#ee7777",
        Token.Aborted:    '#aaaaaa',
        Token.Prompt.BeforeInput: 'bold',

        Token.Operator:       '#33aa33 bold',
        Token.Number:         '#aa3333 bold',

        Token.Menu.Completions.Completion.Current: 'bg:#00aaaa #000000',
        Token.Menu.Completions.Completion:         'bg:#008888 #ffffff',
        Token.Menu.Completions.ProgressButton:     'bg:#003333',
        Token.Menu.Completions.ProgressBar:        'bg:#00aaaa',
    }


if __name__ == '__main__':
    g = create_grammar()
    cli = CommandLineInterface(
        layout=Layout(before_input=DefaultPrompt('Calculate: '),
                      lexer=GrammarLexer(g),
                      menus=[CompletionsMenu()]),
        line=Line(completer=GrammarCompleter(g)),
        style=ExampleStyle)

    try:
        # REPL loop.
        while True:
            # Read input and parse the result.
            document = cli.read_input(on_exit=AbortAction.RAISE_EXCEPTION)
            m = g.match(document.text)
            if m:
                vars = m.variables()
            else:
                print('Invalid command\n')
                continue

            print(vars)
            if vars.get('operator'):
                try:
                    var1 = float(vars.get('var1', 0))
                    var2 = float(vars.get('var2', 0))
                except ValueError:
                    print('Invalid command (2)\n')
                    continue

                # Turn the operator string into a function.
                operator = {
                    'add': (lambda a, b: a + b),
                    'sub': (lambda a, b: a - b),
                    'mul': (lambda a, b: a * b),
                    'div': (lambda a, b: a / b),
                    'sin': (lambda a, b: math.sin(a)),
                }[vars.get('operator')]

                # Execute and print the result.
                print('Result: %s\n' % (operator(var1, var2)))

            elif vars.get('operator2'):
                print('Operator 2')

    except Exit:
        pass
