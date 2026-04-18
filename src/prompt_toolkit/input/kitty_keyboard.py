"""
Decoder for the Kitty keyboard protocol (input side).

Only flag 1 (disambiguate) is currently handled; higher flags (event
types, alternate keys, report-all-as-escape, associated text) are
ignored when volunteered by the terminal.

Ref: https://sw.kovidgoyal.net/kitty/keyboard-protocol/

Wire format:

    CSI <keycode>[:<alt>][;<modifiers>[:<event-type>][;<text-codepoints>]] u

- `keycode`   Unicode codepoint for printable keys, or one of the
              Kitty "functional-key" codes below (Enter=13, Escape=27,
              Arrow Up=57352, F1=57364, …).
- `modifiers` Wire value = 1 + bitmask over (Shift=1, Alt=2, Ctrl=4,
              Super=8, Hyper=16, Meta=32, CapsLock=64, NumLock=128).
              Omitted when no modifiers are active.
- Alt-keys, event-type, and associated text are reported only under
  higher protocol flags that require progressive enhancement.

The decoder returns something the existing `Vt100Parser._call_handler`
already knows how to dispatch: a single `Keys` enum value, a tuple whose
elements are `Keys` or `str`, or `None` when we can't decode (the parser
then falls through to its generic handling).
"""

from __future__ import annotations

import re

from ..keys import Keys

# Full CSI u match. Parameter bytes are digits, semicolons, colons.
KITTY_CSI_U_RE = re.compile(r"^\x1b\[[\d:;]+u\Z")

# Prefix of a potential CSI u sequence — used by the parser's
# "is-this-a-prefix-of-something-longer?" cache so we keep reading bytes.
KITTY_CSI_U_PREFIX_RE = re.compile(r"^\x1b\[[\d:;]*\Z")

# Response to the `CSI ? u` query — `CSI ? <flags> u`. Only sent by
# terminals that actually implement the protocol. The flags value is
# discarded; the arrival of any response is the capability signal.
KITTY_QUERY_RESPONSE_RE = re.compile(r"^\x1b\[\?\d*u\Z")

# Matching prefix regex so the parser keeps reading bytes. Tight enough
# to require the `?`, otherwise it overlaps with `_cpr_response_prefix_re`.
KITTY_QUERY_RESPONSE_PREFIX_RE = re.compile(r"^\x1b\[\?\d*\Z")


# Modifier bit flags. The on-wire value is `1 + sum(bits)`.
_SHIFT = 1
_ALT = 2
_CTRL = 4
# Super / Hyper / Meta (bits 8 / 16 / 32) — ignored for now; routing
# them to `Keys` values requires progressive enhancement flags beyond
# flag 1 and corresponding new enum entries.
_CAPSLOCK = 64
_NUMLOCK = 128
_IGNORED_MODS = _CAPSLOCK | _NUMLOCK


# Functional-key codes from the Kitty spec, mapped to the nearest
# existing prompt_toolkit `Keys` value. Only keys likely to appear under
# `disambiguate` (flag 1) are included.
_FUNCTIONAL: dict[int, Keys] = {
    13: Keys.ControlM,  # Enter
    9: Keys.ControlI,  # Tab
    27: Keys.Escape,
    127: Keys.ControlH,  # Backspace
    # 57358 = CapsLock,
    # 57359 = ScrollLock,
    # 57360 = NumLock,
    # 57361 = PrintScreen,
    # 57362 = Pause,
    # 57363 = Menu — no corresponding `Keys` enum, so left out of the table.
    57364: Keys.F1,
    57365: Keys.F2,
    57366: Keys.F3,
    57367: Keys.F4,
    57368: Keys.F5,
    57369: Keys.F6,
    57370: Keys.F7,
    57371: Keys.F8,
    57372: Keys.F9,
    57373: Keys.F10,
    57374: Keys.F11,
    57375: Keys.F12,
}


_DecodeResult = Keys | str | tuple[Keys | str, ...] | None


def decode_csi_u(sequence: str) -> _DecodeResult:
    """
    Decode a complete CSI u sequence into a `Keys` value (or a tuple of
    `Keys` / `str`) that `Vt100Parser._call_handler` can dispatch.

    Returns `None` for sequences we don't recognize — the caller treats
    that as "no match" and falls through to its usual handling.
    """
    if not KITTY_CSI_U_RE.match(sequence):
        return None

    parts = sequence[2:-1].split(";")

    keycode_str = parts[0].split(":")[0]
    try:
        keycode = int(keycode_str)
    except ValueError:
        return None

    mods_mask = 0
    if len(parts) >= 2:
        mod_subparts = parts[1].split(":")
        try:
            mod_wire = int(mod_subparts[0])
        except ValueError:
            return None
        # The spec guarantees mod_wire >= 1 (it encodes `1 + bitmask`).
        # A conforming terminal never sends 0 or a negative value; if one
        # does, treat it as malformed. Without this guard, `0 - 1 = -1`
        # turns Python's arbitrary-precision integer into a mask with
        # every bit set, producing phantom Ctrl/Alt/Shift on unmodified
        # keys.
        if mod_wire < 1:
            return None
        mods_mask = mod_wire - 1
        # Event type sub-field: 1=press (default), 2=repeat, 3=release.
        # Under flag 1 only press events should ever be sent, but a
        # non-conformant terminal (or one upgraded to flag 2 by another
        # process sharing the tty — e.g. tmux) may volunteer them. If we
        # decoded them as press events, a c-enter binding that submits
        # the form would fire twice (once on press, once on release).
        # An empty sub-field (`13;5:u`) is technically malformed — the
        # spec has no "omitted sub-parameter means default" rule — but
        # treating it as the default (press) is strictly more forgiving
        # than dropping the keypress on the floor, and matches how the
        # modifier field itself defaults when the whole field is absent.
        if len(mod_subparts) >= 2 and mod_subparts[1] != "":
            try:
                event_type = int(mod_subparts[1])
            except ValueError:
                return None
            if event_type != 1:
                return None

    mods_mask &= ~_IGNORED_MODS  # strip CapsLock / NumLock

    base = _decode_keycode(keycode, mods_mask)
    if base is None:
        return None

    # Alt prefix: emit (Escape, base_key), matching prompt_toolkit's
    # long-standing convention for meta-prefixed keys.
    if mods_mask & _ALT:
        if isinstance(base, tuple):
            return (Keys.Escape,) + base
        return (Keys.Escape, base)
    return base


def _decode_keycode(keycode: int, mods: int) -> _DecodeResult:
    """
    Resolve a (keycode, modifier-mask) pair to the best `Keys` value,
    raw character, or tuple thereof.

    `keycode` is either a Kitty functional-key code (see `_FUNCTIONAL`)
    or a Unicode codepoint for a printable key. `mods` is the decoded
    bitmask (already with CapsLock / NumLock stripped and the wire-level
    `+1` removed). The Alt bit is left in place: the caller uses it to
    decide whether to wrap the result in `(Keys.Escape, …)`, so the
    returned value here is the base key *without* the meta prefix.

    Returns `None` when the keycode isn't one we recognize; the caller
    treats that as "no match".
    """
    ctrl = bool(mods & _CTRL)
    shift = bool(mods & _SHIFT)

    if keycode in _FUNCTIONAL:
        return _apply_modifiers(_FUNCTIONAL[keycode], ctrl, shift)

    # Printable Unicode keys with meaningful modifiers.
    if 32 <= keycode <= 0x10FFFF:
        char = chr(keycode)

        if "a" <= char <= "z":
            if ctrl:
                # No distinct `Keys.ControlShiftA` etc.; the Shift bit is
                # silently folded into `ControlX`.
                return Keys["Control" + char.upper()]
            # Plain letter (or Alt-prefix letter — the meta wrap is
            # applied one level up in decode_csi_u).
            return char

        if "0" <= char <= "9":
            if ctrl and shift:
                return Keys["ControlShift" + char]
            if ctrl:
                return Keys["Control" + char]
            return char

        # Other printable — just pass through the character.
        return char

    return None


def _apply_modifiers(base: Keys, ctrl: bool, shift: bool) -> Keys:
    """
    Promote a plain functional `Keys` value to its richer Ctrl / Shift /
    Ctrl-Shift variant when prompt_toolkit has an enum for it.

    `base` is one of the unmodified functional keys from `_FUNCTIONAL`
    (Enter, Tab, Escape, arrows, navigation block, F1–F12). `ctrl` and
    `shift` are booleans decoded from the modifier mask; the Alt bit is
    handled one level up in `decode_csi_u`, so it is intentionally not a
    parameter here.

    When no matching richer enum exists (e.g. plain Shift-Enter,
    Shift-Fn, Shift-Backspace), the base key is returned unchanged. The
    caller should treat those as "modifier silently folded away" rather
    than "decode failure".
    """
    if base is Keys.ControlM:  # Enter
        if ctrl and shift:
            return Keys.ControlShiftEnter
        if ctrl:
            return Keys.ControlEnter
        if shift:
            return Keys.ShiftEnter
        return Keys.ControlM

    if base is Keys.ControlI:  # Tab
        if ctrl and shift:
            return Keys.ControlShiftTab
        if ctrl:
            return Keys.ControlTab
        if shift:
            return Keys.BackTab
        return Keys.ControlI

    if base is Keys.Escape:
        if ctrl and shift:
            return Keys.ControlShiftEscape
        if ctrl:
            return Keys.ControlEscape
        if shift:
            return Keys.ShiftEscape
        return Keys.Escape

    if base is Keys.ControlH:  # Backspace (keycode 127)
        if ctrl and shift:
            return Keys.ControlShiftBackspace
        if ctrl:
            return Keys.ControlBackspace
        if shift:
            return Keys.ShiftBackspace
        return Keys.ControlH

    # F1..F24 — Ctrl+ is a distinct enum; Shift+ is mapped to FN+12 in
    # prompt_toolkit's existing convention (F1 → F13 etc.), but we don't
    # emulate that here; Shift+Fn just returns Fn for now.
    if base.value.startswith("f") and base.value[1:].isdigit():
        if ctrl:
            ctrl_key: Keys | None = getattr(Keys, "Control" + base.name, None)
            if ctrl_key is not None:
                return ctrl_key
        return base

    return base
