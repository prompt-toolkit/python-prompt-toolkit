#!/usr/bin/env python
"""
Demonstrate bug in threaded history, where asynchronous loading can corrupt Buffer context.

Seems to happen with very large history being loaded and causing slowdowns.

"""
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.history import History, ThreadedHistory

import re


class MegaHistory(History):
    """
    Example class that loads lots of history

    Sample designed to exercise existing multitasking hazards, don't add any more.
    """

    def __init__(self, init_request:int = 1000, *args, **kwargs):
        super(MegaHistory, self).__init__(*args, **kwargs)
        self.requested_count = 0        # only modified by main (requesting) thread
        self.requested_commands = 0     # only modified by main (requesting) thread
        self.actual_count = 0           # only modified by background thread

    def load_history_strings(self):
        while True:
            while self.requested_count <= self.actual_count:
                time.sleep(0.001)   # don't busy loop

            print(f'... starting to load {self.requested_count - self.actual_count:15,d} more items.')
            while self.requested_count > self.actual_count:
                yield f"History item {self.actual_count:15,d}, command number {self.requested_commands}"
                self.actual_count += 1
            print('...done.')            

    def store_string(self, string):
        pass  # Don't store strings.

    # called by main thread, watch out for multitasking hazards.
    def add_request(self, requested:int = 0):
        self.requested_count += requested
        self.requested_commands += 1

    def show(self):
        print(f'Have loaded {self.actual_count:15,d} of {self.requested_count:15,d} in {self.requested_commands} commands.')


HIST_CMD = re.compile(r'^hist (load (\d+)|show)$', re.IGNORECASE)


def main():
    print(
        "Asynchronous loading of history. Notice that the up-arrow will work "
        "for as far as the completions are loaded.\n"
        "Even when the input is accepted, loading will continue in the "
        "background and when the next prompt is displayed.\n"
    )
    mh = MegaHistory()
    our_history = ThreadedHistory(mh)

    # The history needs to be passed to the `PromptSession`. It can't be passed
    # to the `prompt` call because only one history can be used during a
    # session.
    session = PromptSession(history=our_history)

    while True:
        text = session.prompt("Say something: ")
        if text.startswith('hist'):
            m = HIST_CMD.match(text)
            if not m:
                print('eh?')
            else:
                if m[1] == 'show':
                    mh.show()
                elif m[1].startswith('load'):
                    mh.add_request(int(m[2]))
                else:
                    print('eh? hist load nnnnnn\nor hist show')
            pass
        else:
            print("You said: %s" % text)


if __name__ == "__main__":
    main()
