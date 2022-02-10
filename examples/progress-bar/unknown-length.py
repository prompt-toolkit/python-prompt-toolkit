#!/usr/bin/env python
"""
A very simple progress bar which keep track of the progress as we consume an
iterator.
"""
import time

from prompt_toolkit.shortcuts import ProgressBar


def data():
    """
    A generator that produces items. len() doesn't work here, so the progress
    bar can't estimate the time it will take.
    """
    yield from range(1000)


def main():
    with ProgressBar() as pb:
        for i in pb(data()):
            time.sleep(0.1)


if __name__ == "__main__":
    main()
