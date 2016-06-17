#!/usr/bin/env python
"""
Autocompletion example with cursor position not at the end of the completion.

Press [Tab] to complete the current word.
- The first Tab press fills in the common part of all completions
    and shows all the completions. (In the menu)
- Any following tab press cycles through all the possible completions.
"""
from __future__ import unicode_literals
from collections import namedtuple

from prompt_toolkit import prompt, completion
from prompt_toolkit.completion import Completer, Completion

CompletionWithCursorPosition = namedtuple('CompletionWithCursorPosition',
    'text cursor_position')

class CursorPositionCompleter(Completer):
    """
    Simple autocompletion on a list of words with associated cursor positions.

    :param completions: List of CompletionWithCursorPosition namedtuples.
    """
    def __init__(self, completions):
        self.completions = completions

    def get_completions(self, document, complete_event):
        before_cursor = document.get_word_before_cursor()
        return (Completion(c.text, -len(before_cursor), cursor_position=c.cursor_position)
            for c in self.completions
            if c.text.startswith(before_cursor))

completions = {
    CompletionWithCursorPosition('upper_case()', 1),
    CompletionWithCursorPosition('lower_case()', 1),
    CompletionWithCursorPosition('list_add(list:=, element:=)', len(', element:=)')),
    CompletionWithCursorPosition('<html></html>', len('</html>'))
}

comp = CursorPositionCompleter(completions)

def main():
    text = prompt('Input: ', completer=comp,
                  complete_while_typing=False)
    print('You said: %s' % text)


if __name__ == '__main__':
    main()
