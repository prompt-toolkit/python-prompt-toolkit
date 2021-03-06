from prompt_toolkit.data_structures import Point
from prompt_toolkit.key_binding.key_processor import KeyPress, KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.mouse_events import (
    MouseButton,
    MouseEvent,
    MouseEventType,
    MouseModifier,
)
from prompt_toolkit.utils import is_windows

from ..key_bindings import KeyBindings

__all__ = [
    "load_mouse_bindings",
]

# fmt: off
SCROLL_UP   = MouseEventType.SCROLL_UP
SCROLL_DOWN = MouseEventType.SCROLL_DOWN
MOUSE_DOWN  = MouseEventType.MOUSE_DOWN
MOUSE_DRAG  = MouseEventType.MOUSE_DRAG
MOUSE_UP    = MouseEventType.MOUSE_UP

NO_MODIFIER       = MouseModifier.NO_MODIFIER
SHIFT             = MouseModifier.SHIFT
ALT               = MouseModifier.ALT
SHIFT_ALT         = MouseModifier.SHIFT_ALT
CONTROL           = MouseModifier.CONTROL
SHIFT_CONTROL     = MouseModifier.SHIFT_CONTROL
ALT_CONTROL       = MouseModifier.ALT_CONTROL
SHIFT_ALT_CONTROL = MouseModifier.SHIFT_ALT_CONTROL
UNKNOWN_MODIFIER  = MouseModifier.UNKNOWN_MODIFIER

LEFT             = MouseButton.LEFT
MIDDLE           = MouseButton.MIDDLE
RIGHT            = MouseButton.RIGHT
NO_BUTTON        = MouseButton.NO_BUTTON
UNKNOWN_BUTTON   = MouseButton.UNKNOWN_BUTTON
# fmt: on

E = KeyPressEvent


def load_mouse_bindings() -> KeyBindings:
    """
    Key bindings, required for mouse support.
    (Mouse events enter through the key binding system.)
    """
    key_bindings = KeyBindings()

    @key_bindings.add(Keys.Vt100MouseEvent)
    def _(event: E) -> None:
        """
        Handling of incoming mouse event.
        """
        # TypicaL:   "eSC[MaB*"
        # Urxvt:     "Esc[96;14;13M"
        # Xterm SGR: "Esc[<64;85;12M"

        # Parse incoming packet.
        if event.data[2] == "M":
            # Typical.
            mouse_event, x, y = map(ord, event.data[3:])

            # TODO: Is it possible to add modifiers here?
            # fmt: off
            mouse_button,mouse_event_type,mouse_modifier = {
                32: (LEFT           , MOUSE_DOWN , UNKNOWN_MODIFIER), 
                33: (MIDDLE         , MOUSE_DOWN , UNKNOWN_MODIFIER), 
                34: (RIGHT          , MOUSE_DOWN , UNKNOWN_MODIFIER), 
                35: (UNKNOWN_BUTTON , MOUSE_UP   , UNKNOWN_MODIFIER), 

                64: (LEFT           , MOUSE_DRAG , UNKNOWN_MODIFIER), 
                65: (MIDDLE         , MOUSE_DRAG , UNKNOWN_MODIFIER), 
                66: (RIGHT          , MOUSE_DRAG , UNKNOWN_MODIFIER), 
                67: (NO_BUTTON      , MOUSE_DRAG , UNKNOWN_MODIFIER), #Just moving the mouse around without clicking anything
                
                96: (NO_BUTTON      , SCROLL_UP  , UNKNOWN_MODIFIER), 
                97: (NO_BUTTON      , SCROLL_DOWN, UNKNOWN_MODIFIER), 
            }[mouse_event]
            # fmt: on

            # Handle situations where `PosixStdinReader` used surrogateescapes.
            if x >= 0xDC00:
                x -= 0xDC00
            if y >= 0xDC00:
                y -= 0xDC00

            x -= 32
            y -= 32
        else:
            # Urxvt and Xterm SGR.
            # When the '<' is not present, we are not using the Xterm SGR mode,
            # but Urxvt instead.
            data = event.data[2:]
            if data[:1] == "<":
                sgr = True
                data = data[1:]
            else:
                sgr = False

            # Extract coordinates.
            mouse_event, x, y = map(int, data[:-1].split(";"))
            m = data[-1]

            # Parse event type.
            if sgr:
                # fmt: off
                # flake8: noqa E201
                mouse_button,mouse_event_type,mouse_modifier = {
                    ( 0, 'm') : (LEFT, MOUSE_UP, NO_MODIFIER),                # left_up                       0+ + +  =0
                    ( 4, 'm') : (LEFT, MOUSE_UP, SHIFT),                      # left_up     Shift             0+4+ +  =4
                    ( 8, 'm') : (LEFT, MOUSE_UP, ALT),                        # left_up           Alt         0+ +8+  =8
                    (12, 'm') : (LEFT, MOUSE_UP, SHIFT_ALT),                  # left_up     Shift Alt         0+4+8+  =12
                    (16, 'm') : (LEFT, MOUSE_UP, CONTROL),                    # left_up               Control 0+ + +16=16
                    (20, 'm') : (LEFT, MOUSE_UP, SHIFT_CONTROL),              # left_up     Shift     Control 0+4+ +16=20
                    (24, 'm') : (LEFT, MOUSE_UP, ALT_CONTROL),                # left_up           Alt Control 0+ +8+16=24
                    (28, 'm') : (LEFT, MOUSE_UP, SHIFT_ALT_CONTROL),          # left_up     Shift Alt Control 0+4+8+16=28

                    ( 1, 'm') : (MIDDLE, MOUSE_UP, NO_MODIFIER),              # middle_up                     1+ + +  =1
                    ( 5, 'm') : (MIDDLE, MOUSE_UP, SHIFT),                    # middle_up   Shift             1+4+ +  =5
                    ( 9, 'm') : (MIDDLE, MOUSE_UP, ALT),                      # middle_up         Alt         1+ +8+  =9
                    (13, 'm') : (MIDDLE, MOUSE_UP, SHIFT_ALT),                # middle_up   Shift Alt         1+4+8+  =13
                    (17, 'm') : (MIDDLE, MOUSE_UP, CONTROL),                  # middle_up             Control 1+ + +16=17
                    (21, 'm') : (MIDDLE, MOUSE_UP, SHIFT_CONTROL),            # middle_up   Shift     Control 1+4+ +16=21
                    (25, 'm') : (MIDDLE, MOUSE_UP, ALT_CONTROL),              # middle_up         Alt Control 1+ +8+16=25
                    (29, 'm') : (MIDDLE, MOUSE_UP, SHIFT_ALT_CONTROL),        # middle_up   Shift Alt Control 1+4+8+16=29

                    ( 2, 'm') : (RIGHT, MOUSE_UP, NO_MODIFIER),               # right_up                      2+ + +  =2
                    ( 6, 'm') : (RIGHT, MOUSE_UP, SHIFT),                     # right_up    Shift             2+4+ +  =6
                    (10, 'm') : (RIGHT, MOUSE_UP, ALT),                       # right_up          Alt         2+ +8+  =10
                    (14, 'm') : (RIGHT, MOUSE_UP, SHIFT_ALT),                 # right_up    Shift Alt         2+4+8+  =14
                    (18, 'm') : (RIGHT, MOUSE_UP, CONTROL),                   # right_up              Control 2+ + +16=18
                    (22, 'm') : (RIGHT, MOUSE_UP, SHIFT_CONTROL),             # right_up    Shift     Control 2+4+ +16=22
                    (26, 'm') : (RIGHT, MOUSE_UP, ALT_CONTROL),               # right_up          Alt Control 2+ +8+16=26
                    (30, 'm') : (RIGHT, MOUSE_UP, SHIFT_ALT_CONTROL),         # right_up    Shift Alt Control 2+4+8+16=30

                    ( 0, 'M') : (LEFT, MOUSE_DOWN, NO_MODIFIER),              # left_down                     0+ + +  =0
                    ( 4, 'M') : (LEFT, MOUSE_DOWN, SHIFT),                    # left_down   Shift             0+4+ +  =4
                    ( 8, 'M') : (LEFT, MOUSE_DOWN, ALT),                      # left_down         Alt         0+ +8+  =8
                    (12, 'M') : (LEFT, MOUSE_DOWN, SHIFT_ALT),                # left_down   Shift Alt         0+4+8+  =12
                    (16, 'M') : (LEFT, MOUSE_DOWN, CONTROL),                  # left_down             Control 0+ + +16=16
                    (20, 'M') : (LEFT, MOUSE_DOWN, SHIFT_CONTROL),            # left_down   Shift     Control 0+4+ +16=20
                    (24, 'M') : (LEFT, MOUSE_DOWN, ALT_CONTROL),              # left_down         Alt Control 0+ +8+16=24
                    (28, 'M') : (LEFT, MOUSE_DOWN, SHIFT_ALT_CONTROL),        # left_down   Shift Alt Control 0+4+8+16=28

                    ( 1, 'M') : (MIDDLE, MOUSE_DOWN, NO_MODIFIER),            # middle_down                   1+ + +  =1
                    ( 5, 'M') : (MIDDLE, MOUSE_DOWN, SHIFT),                  # middle_down Shift             1+4+ +  =5
                    ( 9, 'M') : (MIDDLE, MOUSE_DOWN, ALT),                    # middle_down       Alt         1+ +8+  =9
                    (13, 'M') : (MIDDLE, MOUSE_DOWN, SHIFT_ALT),              # middle_down Shift Alt         1+4+8+  =13
                    (17, 'M') : (MIDDLE, MOUSE_DOWN, CONTROL),                # middle_down           Control 1+ + +16=17
                    (21, 'M') : (MIDDLE, MOUSE_DOWN, SHIFT_CONTROL),          # middle_down Shift     Control 1+4+ +16=21
                    (25, 'M') : (MIDDLE, MOUSE_DOWN, ALT_CONTROL),            # middle_down       Alt Control 1+ +8+16=25
                    (29, 'M') : (MIDDLE, MOUSE_DOWN, SHIFT_ALT_CONTROL),      # middle_down Shift Alt Control 1+4+8+16=29

                    ( 2, 'M') : (RIGHT, MOUSE_DOWN, NO_MODIFIER),             # right_down                    2+ + +  =2
                    ( 6, 'M') : (RIGHT, MOUSE_DOWN, SHIFT),                   # right_down  Shift             2+4+ +  =6
                    (10, 'M') : (RIGHT, MOUSE_DOWN, ALT),                     # right_down        Alt         2+ +8+  =10
                    (14, 'M') : (RIGHT, MOUSE_DOWN, SHIFT_ALT),               # right_down  Shift Alt         2+4+8+  =14
                    (18, 'M') : (RIGHT, MOUSE_DOWN, CONTROL),                 # right_down            Control 2+ + +16=18
                    (22, 'M') : (RIGHT, MOUSE_DOWN, SHIFT_CONTROL),           # right_down  Shift     Control 2+4+ +16=22
                    (26, 'M') : (RIGHT, MOUSE_DOWN, ALT_CONTROL),             # right_down        Alt Control 2+ +8+16=26
                    (30, 'M') : (RIGHT, MOUSE_DOWN, SHIFT_ALT_CONTROL),       # right_down  Shift Alt Control 2+4+8+16=30

                    (32, 'M') : (LEFT, MOUSE_DRAG, NO_MODIFIER),              # left_drag                     32+ + +  =32
                    (36, 'M') : (LEFT, MOUSE_DRAG, SHIFT),                    # left_drag   Shift             32+4+ +  =36
                    (40, 'M') : (LEFT, MOUSE_DRAG, ALT),                      # left_drag         Alt         32+ +8+  =40
                    (44, 'M') : (LEFT, MOUSE_DRAG, SHIFT_ALT),                # left_drag   Shift Alt         32+4+8+  =44
                    (48, 'M') : (LEFT, MOUSE_DRAG, CONTROL),                  # left_drag             Control 32+ + +16=48
                    (52, 'M') : (LEFT, MOUSE_DRAG, SHIFT_CONTROL),            # left_drag   Shift     Control 32+4+ +16=52
                    (56, 'M') : (LEFT, MOUSE_DRAG, ALT_CONTROL),              # left_drag         Alt Control 32+ +8+16=56
                    (60, 'M') : (LEFT, MOUSE_DRAG, SHIFT_ALT_CONTROL),        # left_drag   Shift Alt Control 32+4+8+16=60

                    (33, 'M') : (MIDDLE, MOUSE_DRAG, NO_MODIFIER),            # middle_drag                   33+ + +  =33
                    (37, 'M') : (MIDDLE, MOUSE_DRAG, SHIFT),                  # middle_drag Shift             33+4+ +  =37
                    (41, 'M') : (MIDDLE, MOUSE_DRAG, ALT),                    # middle_drag       Alt         33+ +8+  =41
                    (45, 'M') : (MIDDLE, MOUSE_DRAG, SHIFT_ALT),              # middle_drag Shift Alt         33+4+8+  =45
                    (49, 'M') : (MIDDLE, MOUSE_DRAG, CONTROL),                # middle_drag           Control 33+ + +16=49
                    (53, 'M') : (MIDDLE, MOUSE_DRAG, SHIFT_CONTROL),          # middle_drag Shift     Control 33+4+ +16=53
                    (57, 'M') : (MIDDLE, MOUSE_DRAG, ALT_CONTROL),            # middle_drag       Alt Control 33+ +8+16=57
                    (61, 'M') : (MIDDLE, MOUSE_DRAG, SHIFT_ALT_CONTROL),      # middle_drag Shift Alt Control 33+4+8+16=61

                    (34, 'M') : (RIGHT, MOUSE_DRAG, NO_MODIFIER),             # right_drag                    34+ + +  =34
                    (38, 'M') : (RIGHT, MOUSE_DRAG, SHIFT),                   # right_drag  Shift             34+4+ +  =38
                    (42, 'M') : (RIGHT, MOUSE_DRAG, ALT),                     # right_drag        Alt         34+ +8+  =42
                    (46, 'M') : (RIGHT, MOUSE_DRAG, SHIFT_ALT),               # right_drag  Shift Alt         34+4+8+  =46
                    (50, 'M') : (RIGHT, MOUSE_DRAG, CONTROL),                 # right_drag            Control 34+ + +16=50
                    (54, 'M') : (RIGHT, MOUSE_DRAG, SHIFT_CONTROL),           # right_drag  Shift     Control 34+4+ +16=54
                    (58, 'M') : (RIGHT, MOUSE_DRAG, ALT_CONTROL),             # right_drag        Alt Control 34+ +8+16=58
                    (62, 'M') : (RIGHT, MOUSE_DRAG, SHIFT_ALT_CONTROL),       # right_drag  Shift Alt Control 34+4+8+16=62

                    (35, 'M') : (NO_BUTTON, MOUSE_DRAG, NO_MODIFIER),         # none_drag                     35+ + +  =35
                    (39, 'M') : (NO_BUTTON, MOUSE_DRAG, SHIFT),               # none_drag   Shift             35+4+ +  =39
                    (43, 'M') : (NO_BUTTON, MOUSE_DRAG, ALT),                 # none_drag         Alt         35+ +8+  =43
                    (47, 'M') : (NO_BUTTON, MOUSE_DRAG, SHIFT_ALT),           # none_drag   Shift Alt         35+4+8+  =47
                    (51, 'M') : (NO_BUTTON, MOUSE_DRAG, CONTROL),             # none_drag             Control 35+ + +16=51
                    (55, 'M') : (NO_BUTTON, MOUSE_DRAG, SHIFT_CONTROL),       # none_drag   Shift     Control 35+4+ +16=55
                    (59, 'M') : (NO_BUTTON, MOUSE_DRAG, ALT_CONTROL),         # none_drag         Alt Control 35+ +8+16=59
                    (63, 'M') : (NO_BUTTON, MOUSE_DRAG, SHIFT_ALT_CONTROL),   # none_drag   Shift Alt Control 35+4+8+16=63

                    (64, 'M') : (NO_BUTTON, SCROLL_UP, NO_MODIFIER),          # scroll_up                     64+ + +  =64
                    (68, 'M') : (NO_BUTTON, SCROLL_UP, SHIFT),                # scroll_up   Shift             64+4+ +  =68
                    (72, 'M') : (NO_BUTTON, SCROLL_UP, ALT),                  # scroll_up         Alt         64+ +8+  =72
                    (76, 'M') : (NO_BUTTON, SCROLL_UP, SHIFT_ALT),            # scroll_up   Shift Alt         64+4+8+  =76
                    (80, 'M') : (NO_BUTTON, SCROLL_UP, CONTROL),              # scroll_up             Control 64+ + +16=80
                    (84, 'M') : (NO_BUTTON, SCROLL_UP, SHIFT_CONTROL),        # scroll_up   Shift     Control 64+4+ +16=84
                    (88, 'M') : (NO_BUTTON, SCROLL_UP, ALT_CONTROL),          # scroll_up         Alt Control 64+ +8+16=88
                    (92, 'M') : (NO_BUTTON, SCROLL_UP, SHIFT_ALT_CONTROL),    # scroll_up   Shift Alt Control 64+4+8+16=92

                    (65, 'M') : (NO_BUTTON, SCROLL_DOWN, NO_MODIFIER),        # scroll_down                   64+ + +  =65
                    (69, 'M') : (NO_BUTTON, SCROLL_DOWN, SHIFT),              # scroll_down Shift             64+4+ +  =69
                    (73, 'M') : (NO_BUTTON, SCROLL_DOWN, ALT),                # scroll_down       Alt         64+ +8+  =73
                    (77, 'M') : (NO_BUTTON, SCROLL_DOWN, SHIFT_ALT),          # scroll_down Shift Alt         64+4+8+  =77
                    (81, 'M') : (NO_BUTTON, SCROLL_DOWN, CONTROL),            # scroll_down           Control 64+ + +16=81
                    (85, 'M') : (NO_BUTTON, SCROLL_DOWN, SHIFT_CONTROL),      # scroll_down Shift     Control 64+4+ +16=85
                    (89, 'M') : (NO_BUTTON, SCROLL_DOWN, ALT_CONTROL),        # scroll_down       Alt Control 64+ +8+16=89
                    (93, 'M') : (NO_BUTTON, SCROLL_DOWN, SHIFT_ALT_CONTROL),  # scroll_down Shift Alt Control 64+4+8+16=93
                }[mouse_event, m]
                # fmt: on
            else:
                mouse_button, mouse_event_type, mouse_modifier = {
                    # TODO: I don't know when this is triggered or how this mode works (though my Hyper terminal seems to use it), so I marked the buttons and modifiers UNKNOWN.
                    # By replacing these UNKNOWN values with the correct values, we can get more functionality in different terminal varieties
                    32: (UNKNOWN_BUTTON, MOUSE_DOWN, UNKNOWN_MODIFIER),
                    35: (UNKNOWN_BUTTON, MOUSE_UP, UNKNOWN_MODIFIER),
                    96: (NO_BUTTON, SCROLL_UP, UNKNOWN_MODIFIER),
                    97: (NO_BUTTON, SCROLL_DOWN, UNKNOWN_MODIFIER),
                }.get(mouse_event, (UNKNOWN_BUTTON, MOUSE_DRAG, UNKNOWN_MODIFIER))

        x -= 1
        y -= 1

        # Only handle mouse events when we know the window height.
        if event.app.renderer.height_is_known and mouse_event_type is not None:
            # Take region above the layout into account. The reported
            # coordinates are absolute to the visible part of the terminal.
            from prompt_toolkit.renderer import HeightIsUnknownError

            try:
                y -= event.app.renderer.rows_above_layout
            except HeightIsUnknownError:
                return

            # Call the mouse handler from the renderer.
            handler = event.app.renderer.mouse_handlers.mouse_handlers[y][x]
            handler(
                MouseEvent(
                    position=Point(x=x, y=y),
                    event_type=mouse_event_type,
                    button=mouse_button,
                    modifier=mouse_modifier,
                )
            )
            # print(MouseEvent(position=Point(x=x, y=y), event_type=mouse_event_type, button=mouse_button, modifier=mouse_modifier)) # Uncomment to debug mouse events

    @key_bindings.add(Keys.ScrollUp)
    def _scroll_up(event: E) -> None:
        """
        Scroll up event without cursor position.
        """
        # We don't receive a cursor position, so we don't know which window to
        # scroll. Just send an 'up' key press instead.
        event.key_processor.feed(KeyPress(Keys.Up), first=True)

    @key_bindings.add(Keys.ScrollDown)
    def _scroll_down(event: E) -> None:
        """
        Scroll down event without cursor position.
        """
        event.key_processor.feed(KeyPress(Keys.Down), first=True)

    @key_bindings.add(Keys.WindowsMouseEvent)
    def _mouse(event: E) -> None:
        """
        Handling of mouse events for Windows.
        """
        assert is_windows()  # This key binding should only exist for Windows.

        # Parse data.
        pieces = event.data.split(";")

        event_type = MouseEventType(pieces[0])
        x = int(pieces[1])
        y = int(pieces[2])

        # Make coordinates absolute to the visible part of the terminal.
        output = event.app.renderer.output

        from prompt_toolkit.output.win32 import Win32Output
        from prompt_toolkit.output.windows10 import Windows10_Output

        if isinstance(output, (Win32Output, Windows10_Output)):
            screen_buffer_info = output.get_win32_screen_buffer_info()
            rows_above_cursor = (
                screen_buffer_info.dwCursorPosition.Y - event.app.renderer._cursor_pos.y
            )
            y -= rows_above_cursor

            # Call the mouse event handler.
            handler = event.app.renderer.mouse_handlers.mouse_handlers[y][x]
            handler(
                MouseEvent(
                    position=Point(x=x, y=y),
                    event_type=event_type,
                    button=UNKNOWN_BUTTON,
                    modifier=UNKNOWN_MODIFIER,
                )
            )

    return key_bindings
