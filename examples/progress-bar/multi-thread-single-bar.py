#!/usr/bin/env python
"""
Example of multi threading processes with ony one progress bar
"""
from prompt_toolkit.shortcuts import ProgressBar
from threading import Thread, Lock
import time

lock = Lock()

def nextt(b):
   lock.acquire()
   next(b)
   lock.release()

def test(b):
    for i in range(10):
        nextt(b)
        time.sleep(.5)

with ProgressBar() as pb:
    total = 100
    thrds = []
    pbr = iter(pb(range(total)))
    for i in range(10):
        t = Thread(target=test, args=(pbr,))
        t.start()
        thrds.append(t)
    for t in thrds:
        t.join()
