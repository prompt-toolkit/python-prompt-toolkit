#!/usr/bin/env python
"""
More complex demonstration of what's possible with the progress bar.
"""
import datetime
import random
import threading
import time

from prompt_toolkit import HTML
from prompt_toolkit.filters import Condition
from prompt_toolkit.shortcuts.progress_bar import (
    ProgressBar,
    get_counter,
    get_progress_bar,
)


def main():
    with ProgressBar(
        title=HTML("<b>Example of many parallel tasks.</b>"),
        bottom_toolbar=HTML("<b>[Control-L]</b> clear  <b>[Control-C]</b> abort"),
    ) as pb:
        done = set()

        # Remove a completed counter after 5 seconds but keep the last 5.
        @Condition
        def ten_seconds_passed():
            counter = get_counter()
            delta = datetime.datetime.now() - counter.stop_time
            if delta.total_seconds() > 10:
                done.add(counter)
                return True
            return False

        @Condition
        def at_least_five_bars():
            if len(done) > 5:
                done.remove(get_counter())
                return True
            return False

        def run_task(label, total, sleep_time):
            """Complete a normal run."""
            for i in pb(
                range(total),
                label=label,
                remove_when_done=ten_seconds_passed & at_least_five_bars,
            ):
                time.sleep(sleep_time)

        def stop_task(label, total, sleep_time):
            """Stop at some random index.

            Breaking out of iteration at some stop index mimics how progress
            bars behave in cases where errors are raised.
            """
            stop_i = random.randrange(total)
            bar = pb(range(total), label=label)
            for i in bar:
                if stop_i == i:
                    bar.label = f"{label} BREAK"
                    break
                time.sleep(sleep_time)

        threads = []

        for i in range(160):
            label = "Task %i" % i
            total = random.randrange(50, 200)
            sleep_time = random.randrange(5, 20) / 100.0

            threads.append(
                threading.Thread(
                    target=random.choice((run_task, stop_task)),
                    args=(label, total, sleep_time),
                )
            )

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
