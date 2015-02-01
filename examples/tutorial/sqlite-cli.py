import sys
import sqlite3

from prompt_toolkit.contrib.shortcuts import get_input
from prompt_toolkit.history import History
from prompt_toolkit.contrib.completers import WordCompleter
from pygments.lexers import SqlLexer
from pygments.style import Style
from pygments.token import Token
from pygments.styles.default import DefaultStyle

sql_completer = WordCompleter(['create', 'select', 'insert', 'drop',
                               'delete', 'from', 'where', 'table'], ignore_case=True)

class DocumentStyle(Style):
    styles = {
        Token.Menu.Completions.Completion.Current: 'bg:#00aaaa #000000',
        Token.Menu.Completions.Completion: 'bg:#008888 #ffffff',
        Token.Menu.Completions.ProgressButton: 'bg:#003333',
        Token.Menu.Completions.ProgressBar: 'bg:#00aaaa',
    }
    styles.update(DefaultStyle.styles)

def main(database):
    history = History()
    connection = sqlite3.connect(database)

    while True:
        text = get_input('> ', lexer=SqlLexer, completer=sql_completer, style=DocumentStyle, history=history)
        if text is None:
            break
        with connection:
            messages = connection.execute(text)
            for message in messages:
                print(message)
    print('GoodBye!')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        db = ':memory:'
    else:
        db = sys.argv[1]

    main(db)
