#!/usr/bin/env python
"""
More complex demonstration of what's possible with the progress bar.
"""
import threading
import time

from prompt_toolkit import HTML
from prompt_toolkit.shortcuts import ProgressBar


def main():
    with ProgressBar(
        title=HTML("<b>Example of many parallel tasks.</b>"),
        bottom_toolbar=HTML("<b>[Control-L]</b> clear  <b>[Control-C]</b> abort"),
    ) as pb:

        def run_task(label, total, sleep_time):
            for i in pb(range(total), label=label):
                time.sleep(sleep_time)

        threads = [
            threading.Thread(target=run_task, args=("First task", 50, 0.1)),
            threading.Thread(target=run_task, args=("Second task", 100, 0.1)),
            threading.Thread(target=run_task, args=("Third task", 8, 3)),
            threading.Thread(target=run_task, args=("Fourth task", 200, 0.1)),
            threading.Thread(target=run_task, args=("Fifth task", 40, 0.2)),
            threading.Thread(target=run_task, args=("Sixth task", 220, 0.1)),
            threading.Thread(target=run_task, args=("Seventh task", 85, 0.05)),
            threading.Thread(target=run_task, args=("Eight task", 200, 0.05)),
        ]

        for t in threads:
            t.daemon = True
            t.start()

        # Wait for the threads to finish. We use a timeout for the join() call,
        # because on Windows, join cannot be interrupted by Control-C or any other
        # signal.
        for t in threads:
            while t.is_alive():
                t.join(timeout=0.5)


if __name__ == "__main__":
    main()
