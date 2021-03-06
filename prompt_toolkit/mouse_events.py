"""
Mouse events.


How it works
------------

The renderer has a 2 dimensional grid of mouse event handlers.
(`prompt_toolkit.layout.MouseHandlers`.) When the layout is rendered, the
`Window` class will make sure that this grid will also be filled with
callbacks. For vt100 terminals, mouse events are received through stdin, just
like any other key press. There is a handler among the key bindings that
catches these events and forwards them to such a mouse event handler. It passes
through the `Window` class where the coordinates are translated from absolute
coordinates to coordinates relative to the user control, and there
`UIControl.mouse_handler` is called.
"""
from enum import Enum

from .data_structures import Point

__all__ = ["MouseEventType", "MouseButton", "MouseModifier", "MouseEvent"]


# fmt: off
class MouseEventType(Enum):
    MOUSE_UP    = "MOUSE_UP"    #Ryan Burgert: This same event type is fired for all three events: left mouse up, right mouse up, or middle mouse up
    MOUSE_DOWN  = "MOUSE_DOWN"  #Ryan Burgert: This implicitly refers to the left mouse down (this event is not fired upon pressing the middle or right mouse buttons. I didn't change it's name because I fear creating incompatiabilities with older code.
    SCROLL_UP   = "SCROLL_UP"
    SCROLL_DOWN = "SCROLL_DOWN"
    MOUSE_DRAG  = "MOUSE_DRAG"  #Triggered when the left   mouse button is held down, and the mouse moves


class MouseButton(Enum):
    LEFT           = "LEFT"
    MIDDLE         = "MIDDLE"
    RIGHT          = "RIGHT"
    NO_BUTTON      = ""                # When we're scrolling, or just moving the mouse and not pressing a button, mouse_event.button=="". The reason it's an empty string is so that bool(MouseButton.NO_BUTTON)==False
    UNKNOWN_BUTTON = "UNKNOWN_BUTTON"  # This is for when we don't know which mouse button was pressed, but we do know that one has been pressed during this mouse event (as opposed to scrolling, for example)


class MouseModifierKey(Enum):
    SHIFT   = "SHIFT"
    ALT     = "ALT"
    CONTROL = "CONTROL"


class MouseModifier(Enum):
    # flake8: noqa E201 E202 E261 
    NO_MODIFIER       = (                                                                     )
    SHIFT             = (MouseModifierKey.SHIFT                                              ,)
    ALT               = (                       MouseModifierKey.ALT                         ,)
    SHIFT_ALT         = (MouseModifierKey.SHIFT,MouseModifierKey.ALT                         ,)
    CONTROL           = (                                            MouseModifierKey.CONTROL,)
    SHIFT_CONTROL     = (MouseModifierKey.SHIFT,                     MouseModifierKey.CONTROL,)
    ALT_CONTROL       = (                       MouseModifierKey.ALT,MouseModifierKey.CONTROL,)
    SHIFT_ALT_CONTROL = (MouseModifierKey.SHIFT,MouseModifierKey.ALT,MouseModifierKey.CONTROL,)
    UNKNOWN_MODIFIER  = ("UNKNOWN") # This is used if we're not sure what modifiers are being used, if any
# fmt: on


class MouseEvent:
    """
    Mouse event, sent to `UIControl.mouse_handler`.

    :param position: `Point` instance.
    :param event_type: `MouseEventType`.
    """

    def __init__(
        self,
        position: Point,
        event_type: MouseEventType,
        button: MouseButton,
        modifier: MouseModifier,
    ) -> None:
        self.position = position
        self.event_type = event_type
        self.button = button
        self.modifier = modifier

    def __repr__(self) -> str:
        return "MouseEvent(%r,%r,%r,%r)" % (
            self.position,
            self.event_type,
            self.button,
            self.modifier,
        )
