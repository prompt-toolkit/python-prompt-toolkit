#!/usr/bin/env python
"""
Simple example of a custom, very slow history, that is loaded asynchronously.

By wrapping it in `ThreadedHistory`, the history will load in the background
without blocking any user interaction.
"""
import asyncio
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.history import History, ThreadedHistory


class SlowHistory(History):
    """
    Example class that loads the history very slowly...
    """

    def load_history_strings(self):
        for i in range(1000):
            time.sleep(1)  # Emulate slowness.
            yield "item-%s" % (i,)

    def store_string(self, string):
        pass  # Don't store strings.


def main():
    print(
        "Asynchronous loading of history. Notice that the up-arrow will work "
        "for as far as the completions are loaded.\n"
        "Even when the input is accepted, loading will continue in the "
        "background and when the next prompt is displayed.\n"
    )

    my_loop = asyncio.get_event_loop()  # creates loop if needed

    # Inform ThreadedHistory which event loop to use
    # when passing lines of history to the prompt.

    our_history = ThreadedHistory(SlowHistory(), my_loop)

    # The history needs to be passed to the `PromptSession`. It can't be passed
    # to the `prompt` call because only one history can be used during a
    # session.
    # Note that PromptSession runs on the thread's current event loop because
    # it was created above and is therefore in synch with ThreadedHistory.
    # PromptSession would create and event loop if it didn't find one
    # already running, but then ThreadedHistory would not work.

    session = PromptSession(history=our_history)

    while True:
        text = session.prompt("Say something: ")
        print("You said: %s" % text)


if __name__ == "__main__":
    main()
