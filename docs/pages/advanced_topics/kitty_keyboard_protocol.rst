.. _kitty_keyboard_protocol:


Kitty keyboard protocol
=======================

Maintainer-facing notes on prompt_toolkit's support for the `Kitty
keyboard protocol <https://sw.kovidgoyal.net/kitty/keyboard-protocol/>`_.

Despite its name, the Kitty protocol is supported by a wide range of
terminal emulators across platforms and is not limited to the Kitty
terminal itself.

Only flag 1 ("disambiguate escape codes") is currently implemented.
The spec also defines progressive-enhancement flags for reporting
press/release/repeat events, alternate keys, all keys as escape codes,
and associated text; none of those are implemented here.


Why
---

Under legacy terminal encodings, many modifier+key combinations are
ambiguous or impossible — :kbd:`c-enter` sends the same ``\r`` as plain
:kbd:`enter`, :kbd:`s-enter` is indistinguishable from :kbd:`enter` on
most terminals, :kbd:`m-b` (Alt-b) is reported as an Esc-prefix that
collides with pressing :kbd:`escape` followed by ``b``. The Kitty
protocol fixes all of this by escaping modified keys into ``CSI u``
sequences with explicit modifier bits.

prompt_toolkit pushes flag 1 ("disambiguate escape codes") on startup
and pops it on exit, so supporting terminals deliver modified keys as
distinct ``Keys`` values, and non-supporting terminals silently keep
their existing behavior.



What the code does
------------------

Output
~~~~~~

``src/prompt_toolkit/output/kitty_keyboard.py`` owns the wire-format
constants and exposes ``kitty_keyboard_protocol(output, flags)`` — a
context manager that pushes the given flags on entry and pops on exit.
A depth counter (lazily attached to the ``Output`` instance by the
context manager, not a first-class field on ``Output``) ensures nested
holders compose correctly: outermost enter pushes and flushes,
outermost exit pops and flushes. Entering a nested context with a
different ``flags`` value raises ``ValueError`` rather than silently
corrupting the terminal's flag stack.

Input
~~~~~

``src/prompt_toolkit/input/kitty_keyboard.py`` owns the ``CSI u``
decoder. Covered:

- Functional keys from the Kitty spec: :kbd:`enter`, :kbd:`tab`,
  :kbd:`escape`, :kbd:`backspace`, arrows, navigation block
  (:kbd:`home` / :kbd:`end` / :kbd:`pageup` / :kbd:`pagedown` /
  :kbd:`insert` / :kbd:`delete`), :kbd:`f1`–:kbd:`f12`. Mapped to the
  nearest existing ``Keys`` value with Shift / Ctrl / Ctrl-Shift
  promotion where an enum exists.
- Printable Unicode keys with Ctrl (mapped to ``Keys.ControlX``) and
  Ctrl+Shift digits (mapped to ``Keys.ControlShift1`` …).
- Alt as a meta prefix: emitted as ``(Keys.Escape, base_key)`` to match
  prompt_toolkit's long-standing convention for meta-prefixed keys, so
  existing bindings like ``('escape', 'b')`` keep working.
- CapsLock and NumLock modifier bits are stripped before decoding so
  terminals that report them don't break bindings.

``src/prompt_toolkit/input/vt100_parser.py`` dispatches ``CSI … u``
sequences to the decoder (after the static ``ANSI_SEQUENCES`` lookup,
so pre-existing fixed-form entries still win) and recognizes the
``CSI ? <flags> u`` query response as ``Keys.KittyKeyboardResponse``.

Renderer and capability detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``Renderer`` pushes flag 1 on first render and pops it on reset. At the
same time it writes a ``CSI ? u`` query. The binding in
``src/prompt_toolkit/key_binding/bindings/kitty_keyboard.py`` consumes
the response and flips ``renderer.kitty_support`` from ``UNKNOWN`` to
``SUPPORTED``. Terminals that don't implement the protocol silently
ignore both the push and the query; ``kitty_support`` stays at
``UNKNOWN`` and the terminal keeps sending legacy byte sequences.
Callers that want to branch on capability (e.g. to surface a hint to
the user) can read ``app.renderer.kitty_support`` — ``Application``
exposes its renderer as a public attribute, and the value is one of
``KittySupport.UNKNOWN`` or ``KittySupport.SUPPORTED`` (imported from
``prompt_toolkit.renderer``).

Legacy xterm ``modifyOtherKeys`` fallback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

prompt_toolkit does **not** push ``\x1b[>4;Nm`` to enable xterm's
``modifyOtherKeys``. But the parser still folds
``CSI 27 ; <mods> ; 13 ~`` (Shift-, Ctrl-, and Ctrl-Shift-Enter under
``modifyOtherKeys``) back to ``Keys.ControlM``. That's a passive
compatibility shim: if a user's terminal or tmux has
``modifyOtherKeys`` enabled independently, modified :kbd:`enter` still
submits the form instead of silently doing nothing. Users who want
distinct bindings for :kbd:`c-enter` / :kbd:`s-enter` need a
Kitty-capable terminal.

New ``Keys`` values
~~~~~~~~~~~~~~~~~~~

- ``Keys.ControlEnter``, ``Keys.ControlShiftEnter``,
  ``Keys.ShiftEnter`` — Kitty-only modifier+Enter distinctions. On
  non-Kitty terminals these bindings don't fire; plain :kbd:`enter`
  fires instead (the protocol-less fallback).
- ``Keys.ControlTab``, ``Keys.ControlShiftTab`` — Kitty-only
  modifier+Tab distinctions. Plain :kbd:`tab` (``Keys.ControlI``) and
  Shift-Tab (``Keys.BackTab``) were already distinguishable; Ctrl-Tab
  and Ctrl-Shift-Tab only come through under the protocol. On
  non-Kitty terminals they fold back to their legacy equivalents.
- ``Keys.ControlEscape``, ``Keys.ControlShiftEscape`` — Kitty-only
  modifier+Escape distinctions, alongside the pre-existing
  ``Keys.ShiftEscape``. Same non-Kitty fallback behavior.
- ``Keys.KittyKeyboardResponse`` — internal sentinel for the query
  response parser-to-binding dispatch.

Backspace (:kbd:`backspace`) is decoded from the Kitty functional-key
code 127, but prompt_toolkit has no distinct ``Keys`` values for
:kbd:`c-backspace` / :kbd:`s-backspace`, so modified Backspace silently
folds back to plain Backspace (``Keys.ControlH``) — same behavior as on
legacy terminals.


What could be done in the future
--------------------------------

Higher flags
~~~~~~~~~~~~

The protocol defines further enhancement flags beyond "disambiguate":

- **Flag 2 — report event types.** Distinguishes press / release /
  repeat. Useful for full-screen apps and tooling; not for a shell.
  Would require adding an ``event_type`` field to ``KeyPress``, which
  is a coordinated API change.
- **Flag 4 — report alternate keys.** Sends the base-layout keycode
  alongside the current-layout one; helpful for non-US keyboard
  layouts where a binding is conceptually on the "unshifted key at
  that position".
- **Flag 8 — report all keys as escape codes.** Even unmodified
  letters arrive as ``CSI u``. Dramatically changes input and needs
  corresponding decoder work.
- **Flag 16 — report associated text.** Only meaningful with flag 8.

More functional keys
~~~~~~~~~~~~~~~~~~~~

The decoder's ``_FUNCTIONAL`` table stops at :kbd:`f12` and omits
keypad / media / system keys (Play, Mute, brightness, Left Super, …)
that Kitty can report. Extending the table and adding matching
``Keys`` values is mechanical.

Press/release-aware bindings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bindings today fire on press only. If flag 2 support is ever added,
``KeyBindings.add`` would need an opt-in parameter for release/repeat
events, and the key processor would need to carry the event type. A
large surface; best tackled together with any flag-2 work.


Wire format reference
---------------------

**Push flags.**
    ``CSI > <flags> u`` pushes ``<flags>`` onto the terminal's stack so
    the pop on exit restores the pre-push state. prompt_toolkit always
    pushes ``flags=1`` (disambiguate). The spec also defines
    ``CSI = <flags> ; <mode> u`` which *modifies* the top of the stack
    in place (mode 1 set, 2 OR, 3 AND-NOT); we don't use it because it
    offers no clean restore.

**Pop flags.**
    ``CSI < u`` pops one entry. ``CSI < N u`` pops N.

**Query flags.**
    ``CSI ? u``; terminal answers ``CSI ? <flags> u`` if supported,
    silence otherwise.

**Key event.**
    ``CSI <keycode>[:<alt>] ; <modifiers>[:<event-type>] ;
    <text-codepoints> u``. Every key, functional or not, terminates in
    ``u`` — that's the whole point of the protocol versus the legacy
    ``CSI <n> ~`` encoding it replaces. Modifiers encode as
    ``1 + bitmask`` — the ``+1`` ensures an omitted modifier field
    can't be confused with "Shift pressed". Keycode is a Unicode
    codepoint for printable keys, functional-key codes otherwise
    (Enter=13, Escape=27, F1=57364, …). Event-type is ``1`` for press,
    ``2`` for repeat, ``3`` for release; under flag 1 only press
    events are sent, but the decoder defensively drops the other two.


Known sharp edges
-----------------

- **Modified Enter does not submit by default.** :kbd:`c-enter`,
  :kbd:`s-enter`, and :kbd:`c-s-enter` are delivered as distinct keys
  on a Kitty-capable terminal, but no binding is attached to them out
  of the box — the default ``accept-line`` handler stays on plain
  :kbd:`enter` only. This is deliberate: if we routed modified Enter
  to ``accept-line``, anyone who has long-standing muscle memory around
  "Ctrl-Enter inserts a newline in a multi-line prompt" would suddenly
  find their input submitted on a Kitty terminal but not elsewhere —
  the same physical gesture doing two different things depending on
  the terminal. Users who want :kbd:`c-enter` to submit can bind it
  explicitly::

    bindings = KeyBindings()

    @bindings.add("c-enter")
    def _(event):
        event.current_buffer.validate_and_handle()

  The same applies to :kbd:`c-tab`, :kbd:`c-s-tab`, :kbd:`c-escape`,
  and :kbd:`c-s-escape` — they're available as distinct keys under the
  protocol, but we don't assign them any default semantics.

- **Tmux pass-through.** Requires ``set -g extended-keys on`` *and* an
  underlying terminal that supports the protocol. If the underlying
  terminal doesn't, tmux swallows the query and ``kitty_support``
  stays at ``UNKNOWN``.
- **Detection latency.** The query response is asynchronous; if a
  terminal is slow, the first few keys may arrive before
  ``kitty_support`` flips to ``SUPPORTED``. That only affects the
  capability signal — the push itself applies immediately, so the
  terminal's first keystroke is already in the new encoding.
- **Functional-key codes are not universal.** The Kitty spec pins
  Enter=13 (which coincides with ``\r``) but implementations disagree
  on some rarer functional codes. Worth spot-checking new ones against
  kitty, ghostty, wezterm, foot.
- **Alt vs. Esc-prefix.** Kitty reports Alt as a modifier; the legacy
  path reports it as ``(Esc, letter)``. The decoder emits
  ``(Keys.Escape, base_key)`` for Alt-prefixed keys to match legacy
  convention — so a binding registered as ``('escape', 'b')`` matches
  Alt-b either way.
