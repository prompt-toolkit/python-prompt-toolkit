import sys
import sqlite3

from prompt_toolkit import CommandLineInterface, AbortAction, Exit
from prompt_toolkit.layout import Layout
from prompt_toolkit.line import Line
from prompt_toolkit.layout.prompt import DefaultPrompt
from prompt_toolkit.layout.menus import CompletionMenu
from prompt_toolkit.completion import Completion, Completer
from pygments.lexers.sql import SqlLexer
from pygments.style import Style
from pygments.token import Token
from pygments.styles.default import DefaultStyle

class SqlCompleter(Completer):
    keywords = ['create', 'select', 'insert', 'drop',
                'delete', 'from', 'where', 'table']

    def get_completions(self, document):
        word_before_cursor = document.get_word_before_cursor()

        for keyword in self.keywords:
            if keyword.startswith(word_before_cursor):
                yield Completion(keyword, -len(word_before_cursor))

class DocumentStyle(Style):
    styles = {
        Token.CompletionMenu.Completion.Current: 'bg:#00aaaa #000000',
        Token.CompletionMenu.Completion: 'bg:#008888 #ffffff',
        Token.CompletionMenu.ProgressButton: 'bg:#003333',
        Token.CompletionMenu.ProgressBar: 'bg:#00aaaa',
    }
    styles.update(DefaultStyle.styles)

def main(database):
    connection = sqlite3.connect(database)
    layout = Layout(before_input=DefaultPrompt('> '),
                    lexer=SqlLexer, menus=[CompletionMenu()])
    line = Line(completer=SqlCompleter())
    cli = CommandLineInterface(style=DocumentStyle, layout=layout, line=line)
    try:
        while True:
            document = cli.read_input(on_exit=AbortAction.RAISE_EXCEPTION)
            with connection:
                messages = connection.execute(document.text)
                for message in messages:
                    print message
    except Exit:
        print 'GoodBye!'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        db = ':memory:'
    else:
        db = sys.argv[1]

    main(db)
