"""
Collection of style transformations.

Think of it as a kind of color post processing after the rendering is done.
This could be used for instance to change the contrast/saturation; swap light
and dark colors or even change certain colors for other colors.

When the UI is rendered, these transformations can be applied right after the
style strings are turned into `Attrs` objects that represent the actual
formatting.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from six import with_metaclass
from colorsys import rgb_to_hls, hls_to_rgb

from .base import ANSI_COLOR_NAMES
from .style import parse_color
from prompt_toolkit.cache import memoized
from prompt_toolkit.filters import to_filter
from prompt_toolkit.utils import to_str

__all__ = [
    'StyleTransformation',
    'SwapLightAndDarkStyleTransformation',
    'ReverseStyleTransformation',
    'SetDefaultColorStyleTransformation',
    'DummyStyleTransformation',
    'ConditionalStyleTransformation',
    'DynamicStyleTransformation',
    'merge_style_transformations',
]


class StyleTransformation(with_metaclass(ABCMeta, object)):
    """
    Base class for any style transformation.
    """
    @abstractmethod
    def transform_attrs(self, attrs):
        """
        Take an `Attrs` object and return a new `Attrs` object.

        Remember that the color formats can be either "ansi..." or a 6 digit
        lowercase hexadecimal color (without '#' prefix).
        """

    def invalidation_hash(self):
        """
        When this changes, the cache should be invalidated.
        """
        return '%s-%s' % (self.__class__.__name__, id(self))


class SwapLightAndDarkStyleTransformation(StyleTransformation):
    """
    Turn dark colors into light colors and the other way around.

    This is meant to make color schemes that work on a dark background usable
    on a light background (and the other way around).

    Notice that this doesn't swap foreground and background like "reverse"
    does. It turns light green into dark green and the other way around.
    Foreground and background colors are considered individually.

    Also notice that when <reverse> is used somewhere and no colors are given
    in particular (like what is the default for the bottom toolbar), then this
    doesn't change anything. This is what makes sense, because when the
    'default' color is chosen, it's what works best for the terminal, and
    reverse works good with that.
    """
    def transform_attrs(self, attrs):
        """
        Return the `Attrs` used when opposite luminosity should be used.
        """
        # Reverse colors.
        attrs = attrs._replace(color=get_opposite_color(attrs.color))
        attrs = attrs._replace(bgcolor=get_opposite_color(attrs.bgcolor))

        return attrs


class ReverseStyleTransformation(StyleTransformation):
    """
    Swap the 'reverse' attribute.

    (This is still experimental.)
    """
    def transform_attrs(self, attrs):
        return attrs._replace(reverse=not attrs.reverse)


class SetDefaultColorStyleTransformation(StyleTransformation):
    """
    Set default foreground/background color for output that doesn't specify
    anything. This is useful for overriding the terminal default colors.

    :param fg: Color string or callable that returns a color string for the
        foreground.
    :param bg: Like `fg`, but for the background.
    """
    def __init__(self, fg, bg):
        self.fg = fg
        self.bg = bg

    def transform_attrs(self, attrs):
        if attrs.bgcolor in ('', 'default'):
            attrs = attrs._replace(bgcolor=parse_color(to_str(self.bg)))

        if attrs.color in ('', 'default'):
            attrs = attrs._replace(color=parse_color(to_str(self.fg)))

        return attrs

    def invalidation_hash(self):
        return (
            'set-default-color',
            to_str(self.fg),
            to_str(self.bg),
        )


class DummyStyleTransformation(StyleTransformation):
    """
    Don't transform anything at all.
    """
    def transform_attrs(self, attrs):
        return attrs

    def invalidation_hash(self):
        # Always return the same hash for these dummy instances.
        return 'dummy-style-transformation'


class DynamicStyleTransformation(StyleTransformation):
    """
    StyleTransformation class that can dynamically returns any
    `StyleTransformation`.

    :param get_style_transformation: Callable that returns a
        :class:`.StyleTransformation` instance.
    """
    def __init__(self, get_style_transformation):
        assert callable(get_style_transformation)
        self.get_style_transformation = get_style_transformation

    def transform_attrs(self, attrs):
        style_transformation = self.get_style_transformation() or DummyStyleTransformation()
        return style_transformation.transform_attrs(attrs)

    def invalidation_hash(self):
        style_transformation = self.get_style_transformation() or DummyStyleTransformation()
        return style_transformation.invalidation_hash()


class ConditionalStyleTransformation(StyleTransformation):
    """
    Apply the style transformation depending on a condition.
    """
    def __init__(self, style_transformation, filter):
        assert isinstance(style_transformation, StyleTransformation)

        self.style_transformation = style_transformation
        self.filter = to_filter(filter)

    def transform_attrs(self, attrs):
        if self.filter():
            return self.style_transformation.transform_attrs(attrs)
        return attrs

    def invalidation_hash(self):
        return (
            self.filter(),
            self.style_transformation.invalidation_hash()
        )


class _MergedStyleTransformation(StyleTransformation):
    def __init__(self, style_transformations):
        self.style_transformations = style_transformations

    def transform_attrs(self, attrs):
        for transformation in self.style_transformations:
            attrs = transformation.transform_attrs(attrs)
        return attrs

    def invalidation_hash(self):
        return tuple(t.invalidation_hash() for t in self.style_transformations)


def merge_style_transformations(style_transformations):
    """
    Merge multiple transformations together.
    """
    return _MergedStyleTransformation(style_transformations)


# Dictionary that maps ANSI color names to their opposite. This is useful for
# turning color schemes that are optimized for a black background usable for a
# white background.
OPPOSITE_ANSI_COLOR_NAMES = {
    'ansidefault': 'ansidefault',

    'ansiblack': 'ansiwhite',
    'ansired': 'ansibrightred',
    'ansigreen': 'ansibrightgreen',
    'ansiyellow': 'ansibrightyellow',
    'ansiblue': 'ansibrightblue',
    'ansimagenta': 'ansibrightmagenta',
    'ansicyan': 'ansibrightcyan',
    'ansigray': 'ansibrightblack',

    'ansiwhite': 'ansiblack',
    'ansibrightred': 'ansired',
    'ansibrightgreen': 'ansigreen',
    'ansibrightyellow': 'ansiyellow',
    'ansibrightblue': 'ansiblue',
    'ansibrightmagenta': 'ansimagenta',
    'ansibrightcyan': 'ansicyan',
    'ansibrightblack': 'ansigray',
}
assert set(OPPOSITE_ANSI_COLOR_NAMES.keys()) == set(ANSI_COLOR_NAMES)
assert set(OPPOSITE_ANSI_COLOR_NAMES.values()) == set(ANSI_COLOR_NAMES)


@memoized()
def get_opposite_color(colorname):
    """
    Take a color name in either 'ansi...' format or 6 digit RGB, return the
    color of opposite luminosity (same hue/saturation).

    This is used for turning color schemes that work on a light background
    usable on a dark background.
    """
    # Special values.
    if colorname in ('', 'default'):
        return colorname

    # Try ANSI color names.
    try:
        return OPPOSITE_ANSI_COLOR_NAMES[colorname]
    except KeyError:
        # Try 6 digit RGB colors.
        r = int(colorname[:2], 16) / 255.0
        g = int(colorname[2:4], 16) / 255.0
        b = int(colorname[4:6], 16) / 255.0

        h, l, s = rgb_to_hls(r, g, b)

        l = 1 - l

        r, g, b = hls_to_rgb(h, l, s)

        r = int(r * 255)
        g = int(g * 255)
        b = int(b * 255)

        return '%02x%02x%02x' % (r, g, b)
