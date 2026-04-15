"""Tests for Kitty keyboard protocol input decoding and output helpers."""

from __future__ import annotations

import io

import pytest

from prompt_toolkit.input.kitty_keyboard import decode_csi_u
from prompt_toolkit.input.vt100_parser import Vt100Parser
from prompt_toolkit.keys import Keys
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.output.kitty_keyboard import (
    KITTY_FLAG_DISAMBIGUATE,
    KITTY_FLAG_REPORT_EVENT_TYPES,
    kitty_keyboard_protocol,
)
from prompt_toolkit.output.vt100 import Vt100_Output
from prompt_toolkit.renderer import KittySupport, Renderer
from prompt_toolkit.styles import Style

# ---------- decoder (unit-level) ----------


@pytest.mark.parametrize(
    "seq,expected",
    [
        # Functional keys with Ctrl / Shift / Ctrl-Shift modifiers.
        ("\x1b[13;5u", Keys.ControlEnter),
        ("\x1b[13;6u", Keys.ControlShiftEnter),
        ("\x1b[13;2u", Keys.ShiftEnter),  # Kitty escapes Shift-Enter reliably
        ("\x1b[13u", Keys.ControlM),  # plain Enter
        ("\x1b[9;2u", Keys.BackTab),  # Shift-Tab
        ("\x1b[9;5u", Keys.ControlTab),
        ("\x1b[9;6u", Keys.ControlShiftTab),
        ("\x1b[27u", Keys.Escape),
        ("\x1b[27;2u", Keys.ShiftEscape),
        ("\x1b[27;5u", Keys.ControlEscape),
        ("\x1b[27;6u", Keys.ControlShiftEscape),
        # NOTE: arrow keys, navigation block (Insert / Delete / Home /
        # End / PageUp / PageDown), and F1–F4 intentionally do *not*
        # appear here. Under flag 1 (disambiguate) — the only flag
        # prompt_toolkit pushes — the Kitty spec keeps these keys in
        # their legacy `CSI <n> ~` / `CSI <letter>` / `SS3 <letter>`
        # encoding even when modified. They travel through
        # `ANSI_SEQUENCES` (see `test_parser_routes_legacy_modified_arrow`
        # below), not through the CSI u decoder. Codepoints 57348–57363
        # are only ever emitted under flag 8 (report-all-as-escape);
        # adding them back belongs with any flag-8 work, not here.
        # Ctrl + letter.
        ("\x1b[97;5u", Keys.ControlA),
        ("\x1b[111;5u", Keys.ControlO),
        ("\x1b[122;5u", Keys.ControlZ),
        # Ctrl + digit.
        ("\x1b[49;5u", Keys.Control1),
        # F-keys.
        ("\x1b[57364u", Keys.F1),
        ("\x1b[57364;5u", Keys.ControlF1),
        # Ctrl + Shift + digit.
        ("\x1b[49;6u", Keys.ControlShift1),
    ],
)
def test_decode_simple(seq, expected):
    assert decode_csi_u(seq) == expected


def test_decode_strips_alternate_key_segment():
    # Format: `CSI <keycode>[:<alt-keycode>] ; <modifiers> u`. We ignore
    # the alternate-key segment; Ctrl-a with alt-key=A should still
    # resolve to Keys.ControlA.
    assert decode_csi_u("\x1b[97:65;5u") == Keys.ControlA


def test_decode_rejects_keycode_above_unicode_max():
    assert decode_csi_u(f"\x1b[{0x110000};1u") is None


def test_decode_alt_prefix_for_letter():
    # Alt-a: modifiers = 1 + 2 = 3 (Alt). Emitted as (Escape, 'a') tuple
    # to match prompt_toolkit's meta-prefix convention.
    assert decode_csi_u("\x1b[97;3u") == (Keys.Escape, "a")


def test_decode_alt_ctrl_letter():
    # Alt-Ctrl-a: modifiers = 1 + 2 + 4 = 7. Expect (Escape, ControlA).
    assert decode_csi_u("\x1b[97;7u") == (Keys.Escape, Keys.ControlA)


def test_decode_ignores_capslock_and_numlock():
    # Ctrl-Enter with CapsLock and NumLock both on: modifiers =
    # 1 + 4 + 64 + 128 = 197. Should still resolve to Ctrl-Enter.
    assert decode_csi_u("\x1b[13;197u") == Keys.ControlEnter


def test_decode_rejects_non_csi_u():
    assert decode_csi_u("\x1b[A") is None
    assert decode_csi_u("") is None
    assert decode_csi_u("hello") is None


def test_decode_rejects_malformed_modifier_wire_value():
    # The spec guarantees the modifier wire value is 1 + bitmask, so
    # anything below 1 is non-conforming. Without guarding, `int("0") - 1
    # == -1` becomes a Python infinite-precision integer mask with every
    # bit set and `\x1b[13;0u` decodes as (Escape, ControlShiftEnter).
    assert decode_csi_u("\x1b[13;0u") is None
    assert decode_csi_u("\x1b[97;0u") is None


def test_decode_rejects_non_numeric_modifier():
    assert decode_csi_u("\x1b[13;au") is None


def test_decode_tolerates_missing_modifier():
    # No modifier segment at all: plain Enter maps back to ControlM.
    assert decode_csi_u("\x1b[13u") == Keys.ControlM


@pytest.mark.parametrize("event_type", [2, 3])
def test_decode_drops_release_and_repeat_events(event_type):
    # Event-type 2 (repeat) and 3 (release) are filtered. Without this,
    # a c-enter binding that submits the form would fire twice on a
    # single keypress on a terminal that volunteers release events
    # (which can happen if another process on the tty — tmux, screen
    # — has pushed flag 2 underneath us).
    assert decode_csi_u(f"\x1b[13;5:{event_type}u") is None
    # Press is event-type 1, with or without the explicit ":1" suffix.
    assert decode_csi_u("\x1b[13;5:1u") == Keys.ControlEnter
    assert decode_csi_u("\x1b[13;5u") == Keys.ControlEnter


def test_decode_rejects_non_numeric_event_type():
    assert decode_csi_u("\x1b[13;5:xu") is None


def test_decode_tolerates_empty_event_type_subfield():
    # `CSI 13;5:u` — modifier field present but event-type sub-parameter
    # empty. Technically malformed (the spec doesn't define an implicit
    # default for a present-but-empty sub-parameter), but dropping the
    # keypress on the floor is strictly worse than treating it as the
    # default `press`. Regression guard against `int("")` raising
    # ValueError and silently eating the key.
    assert decode_csi_u("\x1b[13;5:u") == Keys.ControlEnter
    assert decode_csi_u("\x1b[97;5:u") == Keys.ControlA


# ---------- parser integration ----------


class _Collector:
    def __init__(self):
        self.presses = []

    def __call__(self, kp):
        self.presses.append(kp)


def test_parser_routes_kitty_sequences():
    c = _Collector()
    p = Vt100Parser(c)
    p.feed("\x1b[13;5u")  # Ctrl-Enter
    p.feed("\x1b[111;5u")  # Ctrl-O
    p.feed("\x0d")  # legacy plain Enter should still work
    assert [kp.key for kp in c.presses] == [
        Keys.ControlEnter,
        Keys.ControlO,
        Keys.ControlM,
    ]


def test_parser_routes_alt_letter_as_escape_prefix_tuple():
    # Alt+a (modifier = 1 + 2 = 3). decode_csi_u returns the tuple
    # `(Keys.Escape, "a")`, and `_call_handler` should split that into
    # two KeyPress events — Escape with the full raw sequence in `data`,
    # and the literal "a" with empty `data` so we don't double-insert.
    c = _Collector()
    p = Vt100Parser(c)
    raw = "\x1b[97;3u"
    p.feed(raw)
    assert [kp.key for kp in c.presses] == [Keys.Escape, "a"]
    assert c.presses[0].data == raw
    assert c.presses[1].data == ""


@pytest.mark.parametrize(
    "raw",
    [
        "\x1b[27;2;13~",  # Shift-Enter via xterm modifyOtherKeys
        "\x1b[27;5;13~",  # Ctrl-Enter via xterm modifyOtherKeys
        "\x1b[27;6;13~",  # Ctrl-Shift-Enter via xterm modifyOtherKeys
    ],
)
def test_xterm_csi_27_enter_variants_fall_back_to_plain_enter(raw):
    # prompt_toolkit doesn't implement xterm's modifyOtherKeys itself,
    # but a terminal whose user configuration has it on will still send
    # these sequences. Map all three to plain Enter so modifier+Enter at
    # least submits the form, rather than silently doing nothing.
    c = _Collector()
    p = Vt100Parser(c)
    p.feed(raw)
    assert [kp.key for kp in c.presses] == [Keys.ControlM]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("\x1b[1;5A", Keys.ControlUp),
        ("\x1b[1;5B", Keys.ControlDown),
        ("\x1b[1;2C", Keys.ShiftRight),
        ("\x1b[1;6D", Keys.ControlShiftLeft),
        ("\x1b[5;5~", Keys.ControlPageUp),
        ("\x1b[3;2~", Keys.ShiftDelete),
    ],
)
def test_parser_routes_legacy_modified_arrow(raw, expected):
    # Under flag 1 (disambiguate) — the flag prompt_toolkit pushes —
    # modified arrows, navigation keys, and F1–F4 stay in their legacy
    # `CSI … ~` / `CSI … A..D` encoding rather than switching to CSI u.
    # This is what every Kitty-compatible terminal actually sends for
    # Ctrl-Up et al, and it's handled by the static `ANSI_SEQUENCES`
    # table, not the Kitty decoder. Included in this file to keep the
    # real flag-1 coverage close to the CSI u coverage above.
    c = _Collector()
    p = Vt100Parser(c)
    p.feed(raw)
    assert [kp.key for kp in c.presses] == [expected]


def test_parser_prefers_static_table_over_generic_decoder():
    # mintty's own Ctrl+digit encoding is `CSI 1 ; 5 <letter>`
    # (https://github.com/mintty/mintty/wiki/Keycodes), which happens to
    # terminate in `u`. The static ANSI_SEQUENCES entry must still win
    # over the generic Kitty CSI u decoder so Ctrl-5 keeps mapping to
    # `Keys.Control5` rather than being reinterpreted.
    c = _Collector()
    p = Vt100Parser(c)
    p.feed("\x1b[1;5u")
    assert [kp.key for kp in c.presses] == [Keys.Control5]


def test_parser_preserves_insert_text_for_kitty_sequence():
    c = _Collector()
    p = Vt100Parser(c)
    raw = "\x1b[13;5u"
    p.feed(raw)
    # The decoded KeyPress carries the original raw sequence as `data`.
    assert c.presses[0].data == raw


# ---------- output helpers ----------


def _buf_output() -> tuple[io.StringIO, Vt100_Output]:
    buf = io.StringIO()
    return buf, Vt100_Output(buf, lambda: (24, 80), term="xterm")


def test_output_push_and_pop():
    buf, out = _buf_output()
    with kitty_keyboard_protocol(out):
        pass
    out.flush()
    assert buf.getvalue() == "\x1b[>1u\x1b[<u"


def test_output_custom_flags():
    buf, out = _buf_output()
    flags = KITTY_FLAG_DISAMBIGUATE | KITTY_FLAG_REPORT_EVENT_TYPES
    with kitty_keyboard_protocol(out, flags=flags):
        pass
    out.flush()
    assert buf.getvalue() == f"\x1b[>{flags}u\x1b[<u"


def test_output_nested_does_not_double_push():
    buf, out = _buf_output()
    with kitty_keyboard_protocol(out):
        with kitty_keyboard_protocol(out):
            pass
    out.flush()
    # Push once, pop once — nested enter is invisible at the wire level.
    assert buf.getvalue() == "\x1b[>1u\x1b[<u"


def test_output_pop_on_exception():
    buf, out = _buf_output()
    with pytest.raises(RuntimeError):
        with kitty_keyboard_protocol(out):
            raise RuntimeError("boom")
    out.flush()
    assert buf.getvalue().endswith("\x1b[<u")


def test_output_push_is_flushed_before_yield():
    # Callers that wait for a CSI ? u response inside the `with` block
    # rely on the push bytes having actually reached the terminal — not
    # stuck in the output buffer.
    buf, out = _buf_output()
    with kitty_keyboard_protocol(out):
        assert "\x1b[>1u" in buf.getvalue()


def test_output_nested_with_mismatched_flags_raises():
    _, out = _buf_output()
    with kitty_keyboard_protocol(out, flags=1):
        with pytest.raises(ValueError, match="Mixing flags"):
            with kitty_keyboard_protocol(out, flags=3):
                pass


# ---------- renderer capability detection ----------


def test_renderer_report_kitty_keyboard_response_flips_capability():
    # The binding in key_binding/bindings/kitty_keyboard.py calls this
    # method when a `CSI ? <flags> u` response arrives; it's the only
    # transition from UNKNOWN -> SUPPORTED, so the state machine is
    # worth guarding directly.
    renderer = Renderer(Style([]), DummyOutput(), full_screen=False)
    assert renderer.kitty_support is KittySupport.UNKNOWN
    renderer.report_kitty_keyboard_response()
    assert renderer.kitty_support is KittySupport.SUPPORTED
