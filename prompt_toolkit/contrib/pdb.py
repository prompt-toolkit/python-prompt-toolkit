#!/usr/bin/env python
"""
Python debugger prompt.
Enhanced version of Pdb, using a prompt-toolkit front-end.

Usage::

    from prompt_toolkit.contrib.pdb import set_trace
    set_trace()
"""
from __future__ import unicode_literals, absolute_import
from pygments.lexers import PythonLexer
from pygments.token import Token

from prompt_toolkit import CommandLineInterface, AbortAction, Exit

from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.contrib.python_input import PythonCompleter, PythonValidator, PythonStyle
from prompt_toolkit.contrib.regular_languages.compiler import compile
from prompt_toolkit.contrib.regular_languages.completion import GrammarCompleter
from prompt_toolkit.contrib.regular_languages.validation import GrammarValidator
from prompt_toolkit.contrib.regular_languages.grammar import CharacterSet, Regex, Variable, Repeat, Repeat1, Literal
from prompt_toolkit.contrib.regular_languages.lexer import GrammarLexer
from prompt_toolkit.layout.toolbars import SystemToolbar, ValidationToolbar, TextToolbar, ArgToolbar
from prompt_toolkit.layout.toolbars import Toolbar

from prompt_toolkit.history import History
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.prompt import DefaultPrompt
from prompt_toolkit.line import Line

import bdb
import linecache
import pdb
import platform
import sys
import weakref

__all__ = (
    'set_trace',
    'PtPdb',
)


commands_with_help = {
    'alias': "Creates an alias called 'name' the executes 'command'.",
    'args': 'Print the arguments of the current function.',
    'break': 'Set a break',
    'clear': 'Clear breakpoints',
    'commands': '',
    'condition': 'Make breakpoint conditional.',
    'cont': 'Continue execution, only stop when a breakpoint is encountered.',
    'continue': 'Continue execution, only stop when a breakpoint is encountered.',
    'debug': 'Enter a recursive debugger',
    'disable': 'Disable breakpoints',
    'down': 'Move the current frame one level down in the stack trace',
    'enable': 'Enables breakpoints',
    'exit': 'The program being executed is aborted.',
    'help': 'Help',
    'ignore': 'Sets the ignore count for the given breakpoint number.',
    'jump': 'Set the next line that will be executed.',
    'list': 'List source code',
    'next': 'Continue execution until the next line.',
    'p': 'Print the value of the expression',
    'pp': 'Pretty-print expression',
    'quit': 'The program being executed is aborted.',
    'restart': 'Restart the debugged python program.',
    'return': 'Continue execution until the current function returns.',
    'run': 'Restart the debugged python program.',
    'step': 'Execute the current line, stop at the first possible occasion',
    'tbreak': 'Set a break, remove when first hit.',
    'unalias': 'Delete an alias.',
    'up': 'Move the current frame one level up in the stack trace',
    'whatis': 'Prints the type of the argument.',
    'where': 'Print a stack trace,',
}

aliases = {
    'bt': 'where',
    'b': 'break',
    'l': 'list',
    'h': 'help',
    'cl': 'clear',
    'a': 'args',
    'd': 'down',
    'q': 'quit',
    'n': 'next',
    'u': 'up',
    'r': 'return',
    'w': 'where',
    's': 'step',
}


completion_hints = [
    (('help', ), '<command>'),
    (['l', 'list'], '[<first> [<last>]]'),
    (['cl', 'clear'], '[<filename>:<lineno> | <bpnumber>...]'),
    (('j', 'jump'), '<lineno>'),
    (('restart', 'run'), '[<args>...]'),
    (('p', 'pp', 'whatis'), '<expression>'),
    (('enable', 'disable'), '<bpnumber>...'),
    (('ignore', ), '<bpnumber> <count>'),
    (('condition', ), '<bpnumber> <str_condition>'),
    (('alias', ), '<name> [<command> [<parameter>...]]'),
    (('unalias', ), '<name>'),
    (('b', 'break', 'tbreak'), '([<file>:]<lineno> | <function>) [, <condition>]'),
]


class CompletionHint(object):
    """
    Completion hint to be shown after the input.
    """
    def write(self, cli, screen):
        if not (cli.is_exiting or cli.is_aborting or cli.is_returning):
            screen.write_highlighted(self._tokens(cli))

    def _tokens(self, cli):
        words = cli.line.document.text.split()
        if len(words) == 1:
            word = words[0]

            for commands, help in completion_hints:
                if word in commands:
                    return self._highlight_completion(' ' + help)

        return []

    def _highlight_completion(self, text):
        """
        Choose tokens for special characters in the text of the completion
        hint.
        """
        def highlight_char(c):
            if c in '[:]|.()':
                return Token.CompletionHint.Symbol, c
            else:
                return Token.CompletionHint.Parameter, c
        return [highlight_char(c) for c in text]


class BreakPointListCompleter(WordCompleter):
    """
    Complter for breakpoint numbers.
    """
    def __init__(self, only_disabled=False, only_enabled=False):
        commands = []
        meta_dict = {}

        for bp in bdb.Breakpoint.bpbynumber:
            if bp:
                if only_disabled and bp.enabled:
                    continue
                if only_enabled and not bp.enabled:
                    continue

                commands.append('%s' % bp.number)
                meta_dict['%s' % bp.number] = '%s:%s' % (bp.file, bp.line)

        super(BreakPointListCompleter, self).__init__(
            commands,
            meta_dict=meta_dict)


class AliasCompleter(WordCompleter):
    def __init__(self, pdb):
        super(AliasCompleter, self).__init__(
            pdb.aliases.keys(),
            meta_dict=pdb.aliases)


def create_pdb_grammar(pdb):
    curframe = pdb.curframe

    # Completer for all the pdb commands.
    aliases = pdb.aliases.keys()
    meta_dict = {}
    meta_dict.update(commands_with_help)
    meta_dict.update(dict((k, 'Alias for: %s' % v) for k, v in pdb.aliases.items()))

    pdb_commands_completer = WordCompleter(
        commands_with_help.keys() + aliases,
        meta_dict=meta_dict,
        ignore_case=True)

    # Completer for Python code in the current frame.
    python_completer = PythonCompleter(lambda: curframe.f_globals, lambda: curframe.f_locals)

    # Whitespace.
    optional_whitespace = Repeat(CharacterSet(' \t'))
    required_whitespace = Repeat1(CharacterSet(' \t'))

    def create_g(recursive=True):
        return (
            (
                # Help, is followed by a commands completer.
                Variable(Literal('p') | Literal('pp') | Literal('whatis'), token=Token.PdbCommand) +
                required_whitespace +
                Variable(Repeat1(Regex(r'.')), completer=python_completer, lexer=PythonLexer, validator=PythonValidator())
            ) |
            (
                # Enable breakpoints.
                Variable(Literal('enable'), token=Token.PdbCommand) +
                required_whitespace +
                Variable(Repeat1(Regex(r'.')), completer=BreakPointListCompleter(only_disabled=True))
            ) |
            (
                # Disable breakpoints.
                Variable(Literal('disable'), token=Token.PdbCommand) +
                required_whitespace +
                Variable(Repeat1(Regex(r'.')), completer=BreakPointListCompleter(only_enabled=True))
            ) |
            (
                # Condition
                Variable(Literal('condition'), token=Token.PdbCommand) +
                required_whitespace +
                Variable(Repeat1(Regex(r'[0-9]')), completer=BreakPointListCompleter()) +
                required_whitespace +
                Variable(Repeat1(Regex(r'.')), completer=python_completer, lexer=PythonLexer, validator=PythonValidator())
            ) |
            (
                # Break
                Variable(Literal('break') | Literal('b') | Literal('tbreak'), token=Token.PdbCommand) +
                required_whitespace +
                Repeat1(CharacterSet(r'^\s')) +
                optional_whitespace +
                Literal(',') +
                optional_whitespace +
                Variable(Repeat1(Regex(r'.')), completer=python_completer, lexer=PythonLexer, validator=PythonValidator())
            ) |
            (
                # Igore
                Variable(Literal('ignore'), token=Token.PdbCommand) +
                required_whitespace +
                Variable(Repeat1(Regex(r'[0-9]')), completer=BreakPointListCompleter()) +
                required_whitespace +
                Repeat1(Regex(r'[0-9]'))
            ) |
            (
                # Alias
                Variable(Literal('alias'), token=Token.PdbCommand) +
                required_whitespace +
                Repeat1(CharacterSet(r'^\s')) +
                required_whitespace +
                # (recursive grammar)
                (create_g(False) if recursive else Repeat1(Regex('.')))
            ) |
            (
                # Unalias
                Variable(Literal('unalias'), token=Token.PdbCommand) +
                required_whitespace +
                Variable(Repeat1(CharacterSet(r'^\s')), completer=AliasCompleter(pdb))
            ) |
            (
                # Help, is followed by a commands completer.
                Variable(Literal('h') | Literal('help'), token=Token.PdbCommand) +
                required_whitespace +
                Variable(Repeat1(CharacterSet(r'^\s')), completer=pdb_commands_completer)
            ) |
            (
                # Catch all for all other autocompletions.
                Variable(Repeat1(CharacterSet(r'a-zA-Z')), completer=pdb_commands_completer, token=Token.PdbCommand) +
                required_whitespace +
                Repeat1(Regex('.'))
            )
        )

    grammar = (
        optional_whitespace +
        create_g() +
        optional_whitespace
    )
    return compile(grammar)


class SourceCodeToolbar(TextToolbar):
    def __init__(self, pdb_ref):
        super(SourceCodeToolbar, self).__init__(
            lexer=PythonLexer,
            height=7,
            text=self._get_source_code(pdb_ref))

    def _get_source_code(self, pdb_ref):
        """
        Return source code around current line as string.
        (Partly taken from Pdb.do_list.)
        """
        pdb = pdb_ref()

        filename = pdb.curframe.f_code.co_filename
        breaklist = pdb.get_file_breaks(filename)

        first = max(1,  pdb.curframe.f_lineno - 3)
        last = first + 6

        result = []

        for lineno in range(first, last+1):
            line = linecache.getline(filename, lineno, pdb.curframe.f_globals)
            if not line:
                line = '[EOF]'
                break
            else:
                s = repr(lineno).rjust(3)
                if len(s) < 4:
                    s = s + ' '
                if lineno in breaklist:
                    s = s + 'B'
                else:
                    s = s + ' '
                if lineno == pdb.curframe.f_lineno:
                    s = s + '->'

                result.append(s + ' ' + line)

        return ''.join(result)


class PdbStatusToolbar(Toolbar):
    """
    Toolbar which shows the Pdb status. (current line and line number.)
    """
    def __init__(self, pdb_ref, token=None):
        self._pdb_ref = pdb_ref
        token = token or Token.Toolbar.Status
        super(PdbStatusToolbar, self).__init__(token=token)

    def get_tokens(self, cli, width):
        result = []
        append = result.append
        TB = self.token
        pdb = self._pdb_ref()

        # Filename and line number.
        append((TB, ' Break at: '))
        append((TB.Pdb.Filename, pdb.curframe.f_code.co_filename or 'None'))
        append((TB, ' '))
        append((TB.Pdb.Lineno, ': %s' % pdb.curframe.f_lineno))

        # Python version
        version = sys.version_info
        append((TB, ' - '))
        append((TB.PythonVersion, '%s %i.%i.%i' % (platform.python_implementation(),
               version[0], version[1], version[2])))

        return result


class PdbStyle(PythonStyle):
    styles = {
        # Pdb tokens.
        Token.Prompt.BeforeInput:                     'bold #008800',
        Token.PdbCommand:                             'bold',
        Token.CompletionHint.Symbol:                  '#9a8888',
        Token.CompletionHint.Parameter:               '#ba4444 bold',
        Token.Toolbar.Status.Pdb.Filename:            'bg:#222222 #aaaaaa',
        Token.Toolbar.Status.Pdb.Lineno:              'bg:#222222 #ffffff',
    }
    styles.update(PythonStyle.styles)


class PtPdb(pdb.Pdb):
    def __init__(self):
        pdb.Pdb.__init__(self)

        # Create history class.
        self._command_line_history = History()

    def cmdloop(self, intro=None):
        """
        Copy/Paste of pdb.Pdb.cmdloop. But using our own CommandLineInterface.
        """
        self.preloop()

        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(str(self.intro)+"\n")
        stop = None
        while not stop:
            if self.cmdqueue:
                line = self.cmdqueue.pop(0)
            else:
                if self.use_rawinput:
                    line = self._get_input()

            line = self.precmd(line)
            stop = self.onecmd(line)
            stop = self.postcmd(stop, line)
        self.postloop()

    def _get_input(self):
        """
        Read PDB input. Return input text.
        """
        g = create_pdb_grammar(self)

        empty_line = TextToolbar()
        status_toolbar = PdbStatusToolbar(weakref.ref(self))
        source_code_toolbar = SourceCodeToolbar(weakref.ref(self))

        cli = CommandLineInterface(
            layout=Layout(before_input=DefaultPrompt('(pdb) '),
                          show_tildes=True,
                          min_height=15,
                          lexer=GrammarLexer(g),
                          after_input=CompletionHint(),
                          menus=[CompletionsMenu()],
                          top_toolbars=[empty_line],
                          bottom_toolbars=[
                              SystemToolbar(),
                              ArgToolbar(),
                              source_code_toolbar,
                              ValidationToolbar(),
                              status_toolbar
                          ]),
            line=Line(
                completer=GrammarCompleter(g),
                history=self._command_line_history,
                validator=GrammarValidator(g),
            ),
            style=PdbStyle)

        try:
            return cli.read_input(on_exit=AbortAction.RAISE_EXCEPTION).text
        except Exit:
            # Turn Control-D key press into a 'quit' command.
            return 'q'


def set_trace():
    PtPdb().set_trace(sys._getframe().f_back)
