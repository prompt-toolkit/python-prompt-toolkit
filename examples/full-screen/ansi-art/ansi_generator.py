"""Image to ANSI text Generator."""

from pathlib import Path
import argparse
import os
import sys

from PIL import Image  # type: ignore
from prompt_toolkit.output.vt100 import _256ColorCache  # type: ignore

closest_256_color_index = _256ColorCache()


def _arg_parser() -> argparse.Namespace:
    """Setup ansi_generator argparse."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-i', '--image',
                        type=Path,
                        required=True,
                        help="Input image. ")
    parser.add_argument('--colors-256',
                        action='store_true',
                        help="Use 256 colors.")
    parser.add_argument('--save-as-text',
                        type=Path,
                        help='Save the output as a text file')
    parser.add_argument('--full-height-characters',
                        action='store_true',
                        help='Draw output with full height characters.')
    parser.add_argument('--indentation',
                        type=int,
                        default=2,
                        help='Number of spaces to indent the output.')
    parser.add_argument(
        '--transparent-color',
        help='Comma separated r,g,b values to use as transparent.')
    return parser.parse_args()


def _fg256(index: int) -> str:
    return f'\x1B[38;5;{index}m'


def _bg256(index: int) -> str:
    return f'\x1B[48;5;{index}m'


def _clear_formatting() -> str:
    return '\x1B[m'


def _fg(r, g, b) -> str:
    # pylint: disable=invalid-name
    return f'\x1B[38;2;{r};{g};{b}m'


def _bg(r, g, b) -> str:
    # pylint: disable=invalid-name
    return f'\x1B[48;2;{r};{g};{b}m'


def _draw(image,
          indentation,
          _write,
          transparent_color=None,
          colors_256=False):
    columns, rows = image.size

    # pylint: disable=invalid-name
    for row in range(rows):
        _write(_clear_formatting() + ' ' * indentation)
        for col in range(columns):
            alpha = 255
            r, g, b, *remaining_values = image.getpixel((col, row))

            if remaining_values:
                alpha = remaining_values[0]
            elif transparent_color:
                if (r, g, b) == transparent_color:
                    alpha = 0

            if alpha == 255:
                if colors_256:
                    _write(_bg256(closest_256_color_index[(r, g, b)]))
                else:
                    _write(_bg(r, g, b))
            else:
                _write(_clear_formatting())
            _write(' ')

        _write(_clear_formatting() + '\n')


def _draw_half_height(image,
                      indentation,
                      _write,
                      transparent_color=None,
                      colors_256=False):
    # pylint: disable=invalid-name
    total_columns, total_rows = image.size

    for row in range(0, total_rows, 2):
        _write(_clear_formatting() + ' ' * indentation)
        for col in range(total_columns):
            alpha1 = 255
            alpha2 = 255
            r1, g1, b1, *remaining_values1 = image.getpixel((col, row))
            if remaining_values1:
                alpha1 = remaining_values1[0]
            elif transparent_color:
                if (r1, g1, b1) == transparent_color:
                    alpha1 = 0

            # If out of range, pretend the pixel is transparent
            if row + 1 >= total_rows:
                r2, g2, b2, alpha2 = (0, 0, 0, 0)
            else:
                r2, g2, b2, *remaining_values2 = image.getpixel((col, row + 1))
                if remaining_values2:
                    alpha2 = remaining_values2[0]
                elif transparent_color:
                    if (r2, g2, b2) == transparent_color:
                        alpha2 = 0

            # Box Characters: ▄ ▀ █
            if alpha1 < 255 and alpha2 < 255:
                _write(_clear_formatting() + ' ')
            elif alpha1 == 255 and alpha2 < 255:
                if colors_256:
                    _write(_clear_formatting() +
                           _fg256(closest_256_color_index[(r1, g1, b1)]) + '▀')
                else:
                    _write(_clear_formatting() + _fg(r1, g1, b1) + '▀')
            elif alpha1 < 255 and alpha2 == 255:
                if colors_256:
                    _write(_clear_formatting() +
                           _fg256(closest_256_color_index[(r2, g2, b2)]) + '▄')
                else:
                    _write(_clear_formatting() + _fg(r2, g2, b2) + '▄')
            elif alpha1 == 255 and alpha2 == 255:
                if colors_256:
                    _write(
                        _fg256(closest_256_color_index[(r1, g1, b1)]) +
                        _bg256(closest_256_color_index[(r2, g2, b2)]) + '▀')
                else:
                    _write(_fg(r1, g1, b1) + _bg(r2, g2, b2) + '▀')

        _write(_clear_formatting() + '\n')


def main() -> int:
    """Image to terminal."""

    args = _arg_parser()

    # If using Apple Terminal switch to 256 (8bit) color.
    term_program = os.environ.get('TERM_PROGRAM', '')
    if sys.platform == 'darwin' and 'Apple_Terminal' in term_program:
        args.colors_256 = True

    output_file = sys.stdout
    if args.save_as_text:
        output_file = args.save_as_text.open('w')

    transparent_color = None
    if args.transparent_color:
        transparent_color = tuple(
            int(c) for c in args.transparent_color.split(','))
        assert len(transparent_color) == 3

    with Image.open(args.image) as image:
        if args.full_height_characters:
            _draw(image,
                  args.indentation,
                  output_file.write,
                  transparent_color=transparent_color,
                  colors_256=args.colors_256)
        else:
            _draw_half_height(image,
                              args.indentation,
                              output_file.write,
                              transparent_color=transparent_color,
                              colors_256=args.colors_256)

    output_file.flush()
    if args.save_as_text:
        output_file.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
