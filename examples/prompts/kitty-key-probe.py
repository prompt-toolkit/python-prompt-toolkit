#!/usr/bin/env python
"""
Manual checklist for Kitty keyboard protocol decoding.

Walks through a list of keys, asks you to press each one, and reports
whether the decoded ``Keys`` value matches what the spec says it should
be — together with the raw bytes the terminal actually sent.

Useful for spot-checking the codepoint table after a fix, and for
finding terminals that disagree with the spec on a particular code.

Skip a key with ``s`` (e.g. when you just want to move on); mark a key
as absent with ``n`` (e.g. no Insert on a laptop keyboard); abort with
Ctrl-C.

By default the Kitty protocol is enabled. Use ``--no-kitty`` to test
legacy mode only, or ``--both`` to run the full probe list twice
(first without, then with the protocol) so you can compare side by
side.

Run on a Kitty-protocol terminal (kitty, ghostty, wezterm, foot,
recent Alacritty, iTerm2 with CSI u reporting on, …). On a terminal
that doesn't speak the protocol every prompt will report the legacy
escape sequence — also useful, since you'll see the fallback path.
"""

from __future__ import annotations

import argparse
import os
import select
import sys
import termios
import tty
from typing import NamedTuple

from prompt_toolkit.input.vt100_parser import Vt100Parser
from prompt_toolkit.keys import Keys

_KITTY_PUSH = "\x1b[>1u"
_KITTY_POP = "\x1b[<u"

# ANSI colors
_GREEN = "\x1b[32m"
_RED = "\x1b[31m"
_YELLOW = "\x1b[33m"
_CYAN = "\x1b[36m"
_DIM = "\x1b[2m"
_BOLD = "\x1b[1m"
_RESET = "\x1b[0m"


class Probe(NamedTuple):
    prompt: str  # what to tell the user to press
    expected: Keys  # what we expect the decoder to produce


# Ordered list. The six nav-block entries at the top are the ones the
# original codepoint table got wrong (Home<->PageUp, End<->PageDown,
# Insert/Delete missing); leave them at the front for visibility.
PROBES: list[Probe] = [
    Probe("Home", Keys.Home),
    Probe("End", Keys.End),
    Probe("Page Up", Keys.PageUp),
    Probe("Page Down", Keys.PageDown),
    Probe("Insert", Keys.Insert),
    Probe("Delete", Keys.Delete),
    Probe("Up arrow", Keys.Up),
    Probe("Down arrow", Keys.Down),
    Probe("Left arrow", Keys.Left),
    Probe("Right arrow", Keys.Right),
    Probe("Tab", Keys.ControlI),
    Probe("Shift-Tab", Keys.BackTab),
    Probe("Enter", Keys.ControlM),
    Probe("Ctrl-Enter", Keys.ControlEnter),
    Probe("Shift-Enter", Keys.ShiftEnter),
    Probe("Ctrl-Shift-Enter", Keys.ControlShiftEnter),
    Probe("F1", Keys.F1),
    Probe("Ctrl-F1", Keys.ControlF1),
    Probe("Ctrl-A", Keys.ControlA),
    Probe("Ctrl-Shift-Home", Keys.ControlShiftHome),
]

_PROMPT_WIDTH = max(len(p.prompt) for p in PROBES)
_EXPECT_WIDTH = max(len(p.expected.value) for p in PROBES)


def _read_one_event(fd: int, parser: Vt100Parser, sink: list) -> bytes:
    """
    Block until the user presses something, then return the raw bytes.
    Escape sequences arrive in one read on a sane TTY; we additionally
    coalesce anything that lands within 50ms so a multi-byte CSI doesn't
    get split into two events.
    """
    sink.clear()
    raw = b""
    # Initial blocking read.
    raw += os.read(fd, 1024)
    # Drain anything that arrived together (the rest of a CSI tail, etc.).
    while True:
        ready, _, _ = select.select([fd], [], [], 0.05)
        if not ready:
            break
        raw += os.read(fd, 1024)
    parser.feed(raw.decode("latin-1", errors="replace"))
    return raw


def _format_raw(raw: bytes) -> str:
    parts = []
    for b in raw:
        if b == 0x1B:
            parts.append("ESC")
        elif 0x20 <= b < 0x7F:
            parts.append(chr(b))
        else:
            parts.append(f"\\x{b:02x}")
    return "".join(parts)


def _run_probes(fd: int, *, kitty: bool) -> None:
    """Run the probe list once. If *kitty* is True, enable the protocol."""
    sink: list = []
    parser = Vt100Parser(lambda kp: sink.append(kp))
    pass_count = 0
    fail_count = 0
    skip_count = 0
    nokey_count = 0
    failures: list[tuple[Probe, str, str]] = []
    total = len(PROBES)

    mode_label = f"{_GREEN}kitty ON{_RESET}" if kitty else f"{_YELLOW}kitty OFF{_RESET}"

    try:
        if kitty:
            sys.stdout.write(_KITTY_PUSH)
            sys.stdout.flush()

        sys.stdout.write(
            f"\r\n{_BOLD}=== Kitty keyboard probe ({mode_label}{_BOLD}) ==={_RESET}\r\n"
            f"Press the requested key. {_DIM}'s'{_RESET} to skip. "
            f"{_DIM}'n'{_RESET} for no such key. "
            f"{_DIM}Ctrl-C{_RESET} to abort.\r\n\r\n"
        )
        sys.stdout.flush()

        for i, probe in enumerate(PROBES, 1):
            counter = f"{_DIM}[{i:2d}/{total}]{_RESET}"
            key_name = f"{_BOLD}{probe.prompt:<{_PROMPT_WIDTH}}{_RESET}"
            expect = f"{_DIM}expect {probe.expected.value!r:<{_EXPECT_WIDTH}}{_RESET}"
            sys.stdout.write(f"  {counter} {key_name}  {expect}  ")
            sys.stdout.flush()

            raw = _read_one_event(fd, parser, sink)

            # Skip handling: lone 's' or 'S'.
            if raw in (b"s", b"S") and sink and sink[0].key == "s":
                sys.stdout.write(f"{_YELLOW}SKIP{_RESET}\r\n")
                skip_count += 1
                continue

            # No such key on this keyboard: lone 'n' or 'N'.
            if raw in (b"n", b"N") and sink and sink[0].key == "n":
                sys.stdout.write(f"{_DIM}N/A{_RESET}  {_DIM}(no such key){_RESET}\r\n")
                nokey_count += 1
                continue

            keys_seen = [kp.key for kp in sink]
            actual = (
                keys_seen[0].value
                if isinstance(keys_seen[0], Keys)
                else str(keys_seen[0])
            ) if keys_seen else "<none>"

            raw_pretty = _format_raw(raw)

            if keys_seen and keys_seen[0] == probe.expected:
                sys.stdout.write(
                    f"{_GREEN}{_BOLD}PASS{_RESET}  {_DIM}{raw_pretty}{_RESET}\r\n"
                )
                pass_count += 1
            else:
                sys.stdout.write(
                    f"{_RED}{_BOLD}FAIL{_RESET}  "
                    f"got {_RED}{actual!r}{_RESET}  "
                    f"{_DIM}raw={raw_pretty}{_RESET}\r\n"
                )
                failures.append((probe, actual, raw_pretty))
                fail_count += 1

            sys.stdout.flush()

    except KeyboardInterrupt:
        sys.stdout.write(f"\r\n{_DIM}(aborted){_RESET}\r\n")
    finally:
        if kitty:
            sys.stdout.write(_KITTY_POP)
            sys.stdout.flush()

    # Summary
    print()
    parts = []
    if pass_count:
        parts.append(f"{_GREEN}{pass_count} pass{_RESET}")
    if fail_count:
        parts.append(f"{_RED}{fail_count} fail{_RESET}")
    if skip_count:
        parts.append(f"{_YELLOW}{skip_count} skip{_RESET}")
    if nokey_count:
        parts.append(f"{_DIM}{nokey_count} n/a{_RESET}")
    print(f"{_BOLD}Summary ({mode_label}{_BOLD}):{_RESET} {', '.join(parts)}")

    if failures:
        print(f"\n{_RED}{_BOLD}Mismatches:{_RESET}")
        for probe, actual, raw_pretty in failures:
            print(
                f"  {_CYAN}{probe.prompt:<{_PROMPT_WIDTH}}{_RESET}  "
                f"expected {_GREEN}{probe.expected.value!r:<{_EXPECT_WIDTH}}{_RESET}  "
                f"got {_RED}{actual!r}{_RESET}  "
                f"{_DIM}raw={raw_pretty}{_RESET}"
            )


def main() -> None:
    ap = argparse.ArgumentParser(description="Kitty keyboard protocol probe")
    group = ap.add_mutually_exclusive_group()
    group.add_argument(
        "--kitty", action="store_true", default=True,
        help="enable Kitty protocol (default)",
    )
    group.add_argument(
        "--no-kitty", action="store_true",
        help="run without enabling Kitty protocol (legacy mode)",
    )
    group.add_argument(
        "--both", action="store_true",
        help="run twice: first without Kitty, then with Kitty, to compare",
    )
    args = ap.parse_args()

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)

        if args.both:
            _run_probes(fd, kitty=False)
            sys.stdout.write(
                f"\r\n{_DIM}{'─' * 60}{_RESET}\r\n"
            )
            sys.stdout.flush()
            _run_probes(fd, kitty=True)
        elif args.no_kitty:
            _run_probes(fd, kitty=False)
        else:
            _run_probes(fd, kitty=True)

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


if __name__ == "__main__":
    main()
