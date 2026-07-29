#!/usr/bin/env python3

from prompt_toolkit import Application
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import Dimension as D, sum_layout_dimensions, max_layout_dimensions, to_dimension
from prompt_toolkit.widgets import Box, TextArea, Label, Button
# from prompt_toolkit.widgets.base import Border
from prompt_toolkit.layout.containers import Window, VSplit, HSplit, HorizontalAlign, VerticalAlign
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.utils import take_using_weights


class SpaceBorder:
    " Box drawing characters. (Spaces) "
    HORIZONTAL = ' '
    VERTICAL = ' '

    TOP_LEFT = ' '
    TOP_RIGHT = ' '
    BOTTOM_LEFT = ' '
    BOTTOM_RIGHT = ' '

    LEFT_T = ' '
    RIGHT_T = ' '
    TOP_T = ' '
    BOTTOM_T = ' '

    INTERSECT = ' '


class AsciiBorder:
    " Box drawing characters. (ASCII) "
    HORIZONTAL = '-'
    VERTICAL = '|'

    TOP_LEFT = '+'
    TOP_RIGHT = '+'
    BOTTOM_LEFT = '+'
    BOTTOM_RIGHT = '+'

    LEFT_T = '+'
    RIGHT_T = '+'
    TOP_T = '+'
    BOTTOM_T = '+'

    INTERSECT = '+'


class ThinBorder:
    " Box drawing characters. (Thin) "
    HORIZONTAL = '\u2500'
    VERTICAL = '\u2502'

    TOP_LEFT = '\u250c'
    TOP_RIGHT = '\u2510'
    BOTTOM_LEFT = '\u2514'
    BOTTOM_RIGHT = '\u2518'

    LEFT_T = '\u251c'
    RIGHT_T = '\u2524'
    TOP_T = '\u252c'
    BOTTOM_T = '\u2534'

    INTERSECT = '\u253c'


class RoundedBorder(ThinBorder):
    " Box drawing characters. (Rounded) "
    TOP_LEFT = '\u256d'
    TOP_RIGHT = '\u256e'
    BOTTOM_LEFT = '\u2570'
    BOTTOM_RIGHT = '\u256f'


class ThickBorder:
    " Box drawing characters. (Thick) "
    HORIZONTAL = '\u2501'
    VERTICAL = '\u2503'

    TOP_LEFT = '\u250f'
    TOP_RIGHT = '\u2513'
    BOTTOM_LEFT = '\u2517'
    BOTTOM_RIGHT = '\u251b'

    LEFT_T = '\u2523'
    RIGHT_T = '\u252b'
    TOP_T = '\u2533'
    BOTTOM_T = '\u253b'

    INTERSECT = '\u254b'


class DoubleBorder:
    " Box drawing characters. (Thin) "
    HORIZONTAL = '\u2550'
    VERTICAL = '\u2551'

    TOP_LEFT = '\u2554'
    TOP_RIGHT = '\u2557'
    BOTTOM_LEFT = '\u255a'
    BOTTOM_RIGHT = '\u255d'

    LEFT_T = '\u2560'
    RIGHT_T = '\u2563'
    TOP_T = '\u2566'
    BOTTOM_T = '\u2569'

    INTERSECT = '\u256c'


class Merge:
    def __init__(self, cell, merge=1):
        self.cell = cell
        self.merge = merge

    def __iter__(self):
        yield self.cell
        yield self.merge


class Table(HSplit):
    def __init__(self, table,
                 borders=ThinBorder, column_width=None, column_widths=[],
                 window_too_small=None, align=VerticalAlign.JUSTIFY,
                 padding=0, padding_char=None, padding_style='',
                 width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style=''):
        self.borders = borders
        self.column_width = column_width
        self.column_widths = column_widths

        # ensure the table is iterable (has rows)
        if not isinstance(table, list):
            table = [table]
        children = [_Row(row=row, table=self, borders=borders)
                    for row in table]

        super().__init__(
            children=children,
            window_too_small=window_too_small,
            align=align,
            padding=padding,
            padding_char=padding_char,
            padding_style=padding_style,
            width=width,
            height=height,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style)

    @property
    def columns(self):
        return max(row.raw_columns for row in self.children)

    @property
    def _all_children(self):
        """
        List of child objects, including padding & borders.
        """
        def get():
            result = []

            # Padding top.
            if self.align in (VerticalAlign.CENTER, VerticalAlign.BOTTOM):
                result.append(Window(width=D(preferred=0)))

            # Border top is first inserted in children loop.

            # The children with padding.
            prev = None
            for child in self.children:
                result.append(_Border(
                    prev=prev,
                    next=child,
                    table=self,
                    borders=self.borders))
                result.append(child)
                prev = child

            # Border bottom.
            result.append(_Border(prev=prev, next=None, table=self, borders=self.borders))

            # Padding bottom.
            if self.align in (VerticalAlign.CENTER, VerticalAlign.TOP):
                result.append(Window(width=D(preferred=0)))

            return result

        return self._children_cache.get(tuple(self.children), get)

    def preferred_dimensions(self, width):
        dimensions = [[]] * self.columns
        for row in self.children:
            assert isinstance(row, _Row)
            j = 0
            for cell in row.children:
                assert isinstance(cell, _Cell)

                if cell.merge != 1:
                    dimensions[j].append(cell.preferred_width(width))

                j += cell.merge

        for i, c in enumerate(dimensions):
            yield D.exact(1)

            try:
                w = self.column_widths[i]
            except IndexError:
                w = self.column_width
            if w is None:  # fitted
                yield max_layout_dimensions(c)
            else:  # fixed or weighted
                yield to_dimension(w)
        yield D.exact(1)


class _VerticalBorder(Window):
    def __init__(self, borders):
        super().__init__(width=1, char=borders.VERTICAL)


class _HorizontalBorder(Window):
    def __init__(self, borders):
        super().__init__(height=1, char=borders.HORIZONTAL)


class _UnitBorder(Window):
    def __init__(self, char):
        super().__init__(width=1, height=1, char=char)


class _BaseRow(VSplit):
    @property
    def columns(self):
        return self.table.columns

    def _divide_widths(self, width):
        """
        Return the widths for all columns.
        Or None when there is not enough space.
        """
        children = self._all_children

        if not children:
            return []

        # Calculate widths.
        dimensions = list(self.table.preferred_dimensions(width))
        preferred_dimensions = [d.preferred for d in dimensions]

        # Sum dimensions
        sum_dimensions = sum_layout_dimensions(dimensions)

        # If there is not enough space for both.
        # Don't do anything.
        if sum_dimensions.min > width:
            return

        # Find optimal sizes. (Start with minimal size, increase until we cover
        # the whole width.)
        sizes = [d.min for d in dimensions]

        child_generator = take_using_weights(
            items=list(range(len(dimensions))),
            weights=[d.weight for d in dimensions])

        i = next(child_generator)

        # Increase until we meet at least the 'preferred' size.
        preferred_stop = min(width, sum_dimensions.preferred)

        while sum(sizes) < preferred_stop:
            if sizes[i] < preferred_dimensions[i]:
                sizes[i] += 1
            i = next(child_generator)

        # Increase until we use all the available space.
        max_dimensions = [d.max for d in dimensions]
        max_stop = min(width, sum_dimensions.max)

        while sum(sizes) < max_stop:
            if sizes[i] < max_dimensions[i]:
                sizes[i] += 1
            i = next(child_generator)

        # perform merges if necessary
        if len(children) != len(sizes):
            tmp = []
            i = 0
            for c in children:
                if isinstance(c, _Cell):
                    inc = (c.merge * 2) - 1
                    tmp.append(sum(sizes[i:i + inc]))
                else:
                    inc = 1
                    tmp.append(sizes[i])
                i += inc
            sizes = tmp

        return sizes


class _Row(_BaseRow):
    def __init__(self, row, table, borders,
                 window_too_small=None, align=HorizontalAlign.JUSTIFY,
                 padding=D.exact(0), padding_char=None, padding_style='',
                 width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style=''):
        self.table = table
        self.borders = borders

        # ensure the row is iterable (has cells)
        if not isinstance(row, list):
            row = [row]
        children = []
        for c in row:
            m = 1
            if isinstance(c, Merge):
                c, m = c
            elif isinstance(c, dict):
                c, m = Merge(**c)
            children.append(_Cell(cell=c, table=table, row=self, merge=m))

        super().__init__(
            children=children,
            window_too_small=window_too_small,
            align=align,
            padding=padding,
            padding_char=padding_char,
            padding_style=padding_style,
            width=width,
            height=height,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style)

    @property
    def raw_columns(self):
        return sum(cell.merge for cell in self.children)

    @property
    def _all_children(self):
        """
        List of child objects, including padding & borders.
        """
        def get():
            result = []

            # Padding left.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.RIGHT):
                result.append(Window(width=D(preferred=0)))

            # Border left is first inserted in children loop.

            # The children with padding.
            c = 0
            for child in self.children:
                result.append(_VerticalBorder(borders=self.borders))
                result.append(child)
                c += child.merge
            # Fill in any missing columns
            for _ in range(self.columns - c):
                result.append(_VerticalBorder(borders=self.borders))
                result.append(_Cell(cell=None, table=self.table, row=self))

            # Border right.
            result.append(_VerticalBorder(borders=self.borders))

            # Padding right.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.LEFT):
                result.append(Window(width=D(preferred=0)))

            return result

        return self._children_cache.get(tuple(self.children), get)


class _Border(_BaseRow):
    def __init__(self, prev, next, table, borders,
                 window_too_small=None, align=HorizontalAlign.JUSTIFY,
                 padding=D.exact(0), padding_char=None, padding_style='',
                 width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style=''):
        assert prev or next
        self.prev = prev
        self.next = next
        self.table = table
        self.borders = borders

        children = [_HorizontalBorder(borders=borders)] * self.columns

        super().__init__(
            children=children,
            window_too_small=window_too_small,
            align=align,
            padding=padding,
            padding_char=padding_char,
            padding_style=padding_style,
            width=width,
            height=height or 1,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style)

    def has_borders(self, row):
        yield None  # first (outer) border

        if not row:
            # this row is undefined, none of the borders need to be marked
            yield from [False] * (self.columns - 1)
        else:
            c = 0
            for child in row.children:
                yield from [False] * (child.merge - 1)
                yield True
                c += child.merge

            yield from [True] * (self.columns - c)

        yield None  # last (outer) border

    @property
    def _all_children(self):
        """
        List of child objects, including padding & borders.
        """
        def get():
            result = []

            # Padding left.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.RIGHT):
                result.append(Window(width=D(preferred=0)))

            def char(i, pc=False, nc=False):
                if i == 0:
                    if self.prev and self.next:
                        return self.borders.LEFT_T
                    elif self.prev:
                        return self.borders.BOTTOM_LEFT
                    else:
                        return self.borders.TOP_LEFT

                if i == self.columns:
                    if self.prev and self.next:
                        return self.borders.RIGHT_T
                    elif self.prev:
                        return self.borders.BOTTOM_RIGHT
                    else:
                        return self.borders.TOP_RIGHT

                if pc and nc:
                    return self.borders.INTERSECT
                elif pc:
                    return self.borders.BOTTOM_T
                elif nc:
                    return self.borders.TOP_T
                else:
                    return self.borders.HORIZONTAL

            # Border left is first inserted in children loop.

            # The children with padding.
            pcs = self.has_borders(self.prev)
            ncs = self.has_borders(self.next)
            for i, (child, pc, nc) in enumerate(zip(self.children, pcs, ncs)):
                result.append(_UnitBorder(char=char(i, pc, nc)))
                result.append(child)

            # Border right.
            result.append(_UnitBorder(char=char(self.columns)))

            # Padding right.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.LEFT):
                result.append(Window(width=D(preferred=0)))

            return result

        return self._children_cache.get(tuple(self.children), get)


class _Cell(HSplit):
    def __init__(self, cell, table, row, merge=1,
                 padding=0, char=None,
                 padding_left=None, padding_right=None,
                 padding_top=None, padding_bottom=None,
                 window_too_small=None,
                 width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style=''):
        self.table = table
        self.row = row
        self.merge = merge

        if padding is None:
            padding = D(preferred=0)

        def get(value):
            if value is None:
                value = padding
            return to_dimension(value)

        self.padding_left = get(padding_left)
        self.padding_right = get(padding_right)
        self.padding_top = get(padding_top)
        self.padding_bottom = get(padding_bottom)

        children = []
        children.append(Window(width=self.padding_left, char=char))
        if cell:
            children.append(cell)
        children.append(Window(width=self.padding_right, char=char))

        children = [
            Window(height=self.padding_top, char=char),
            VSplit(children),
            Window(height=self.padding_bottom, char=char),
        ]

        super().__init__(
            children=children,
            window_too_small=window_too_small,
            width=width,
            height=height,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style)


def demo():
    txt1 = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Ut purus nibh, sollicitudin at lorem eget, tristique fringilla purus. Donec sit amet lectus porta, aliquam ligula sed, sagittis eros. Proin in augue leo. Donec vitae erat pellentesque, hendrerit tellus malesuada, mollis urna. Nam varius, lorem id porttitor euismod, erat sapien tempus odio, ac porttitor eros lacus et magna. Nam in arcu pellentesque, bibendum est vel, viverra nulla. Ut ut accumsan risus. Donec at volutpat tortor. Nulla ac elementum lacus. Pellentesque nec nibh tempus, posuere massa nec, consequat lorem. Curabitur ac sollicitudin neque. Donec vel ante magna. Nunc nec sapien vitae sem bibendum volutpat. Donec posuere nulla felis, id mattis risus dictum ut. Fusce libero mi, varius aliquet commodo at, tempus ut eros."
    txt2 = "Praesent eu ultrices massa. Cras et dui bibendum, venenatis urna nec, porttitor sem. Nullam commodo tempor pellentesque. Praesent leo odio, fermentum a ultrices a, ultrices eu nibh. Etiam commodo orci urna, vitae egestas enim ultricies vel. Cras diam eros, rutrum in congue ac, pretium sed quam. Cras commodo ut ipsum ut sollicitudin."
    txt3 = "Proin in varius purus. <b>Aliquam nec nulla</b> eget lorem fermentum facilisis. Quisque eget ante quam. Quisque vel pharetra magna. Sed volutpat, ligula sed aliquam pharetra, felis tellus bibendum mi, at imperdiet risus augue eget eros. Suspendisse ut venenatis magna, at euismod magna. Phasellus bibendum maximus sem eget porttitor. Donec et eleifend mi, in ornare nisi."
    txt4 = "Morbi viverra, justo eget pretium sollicitudin, magna ex sodales ligula, et convallis erat mauris eu urna. Curabitur tristique quis metus at sodales. Nullam tincidunt convallis lorem in faucibus. Donec nec turpis ante. Ut tincidunt neque eu ornare sagittis. Suspendisse potenti. Etiam tellus est, porttitor eget luctus sed, euismod et erat. Vivamus commodo, massa eget mattis eleifend, turpis sem porttitor dolor, eu finibus ex erat id tellus. Etiam viverra iaculis tellus, ut tempus tellus. Maecenas arcu lectus, euismod accumsan erat eu, blandit vehicula dui. Nulla id ante egestas, imperdiet nibh et, fringilla orci. Donec ut pretium est. Vivamus feugiat facilisis iaculis. Pellentesque imperdiet ex felis, ac elementum dolor tincidunt eget. Cras molestie tellus id massa suscipit, hendrerit vulputate metus tincidunt. Aliquam erat enim, rhoncus in metus eu, consequat cursus ipsum."
    txt5 = "Integer at dictum justo. Vestibulum gravida nec diam a iaculis. Nullam non sollicitudin turpis, in mollis augue. In ut interdum magna. Ut tellus eros, blandit a ex a, suscipit varius tortor. Nulla pulvinar nibh vitae tristique tincidunt. Proin eu fringilla nibh. Mauris metus erat, laoreet sed eros ac, maximus finibus turpis. Sed tortor massa, congue nec lacus nec, fringilla fermentum purus. Vivamus eget pretium mi, vel ultricies orci. Phasellus semper viverra lorem. Phasellus velit nisl, scelerisque sit amet vulputate luctus, ullamcorper in velit. Fusce pellentesque elit ut leo tincidunt euismod. Integer nisl ante, dignissim id leo ut, interdum auctor ipsum. Fusce nunc ligula, imperdiet et nisl id, mollis imperdiet erat."
    txt6 = "Ut egestas vel nisi et sodales. Etiam arcu massa, viverra in pellentesque quis, molestie a lacus. Nulla suscipit mi luctus blandit dignissim. Proin ac turpis sit amet enim luctus venenatis quis et orci. Donec sed tortor ex. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. In et turpis sapien. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Vivamus et purus et ex interdum commodo at non velit. Nullam eget diam et felis accumsan gravida non vitae nulla. Morbi tellus mauris, tristique non vulputate eu, efficitur at tellus. Morbi in erat et purus euismod luctus vel vel erat. Fusce auctor augue felis, quis ornare justo mattis vel."
    txt7 = "Etiam quis eros eu urna consequat finibus. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Integer suscipit, est ac blandit cursus, sem diam egestas massa, sit amet dignissim velit nibh in tortor. Fusce scelerisque feugiat ligula vitae pharetra. Fusce mattis placerat volutpat. Aliquam fermentum ligula mauris, sit amet tempor dui elementum nec. Nunc augue felis, egestas ut lacus vitae, placerat condimentum turpis. Nulla volutpat quis felis id tristique. Vivamus non odio et magna dapibus suscipit vitae et dui. Aenean magna lectus, congue eu commodo luctus, dapibus vel sem. Quisque nec diam consequat, luctus nisi vitae, rutrum mi. Nullam consectetur non risus eleifend dignissim. Vivamus sit amet sagittis libero. Integer nec ipsum fringilla, pulvinar ex vitae, aliquet est. Etiam sit amet est finibus, facilisis erat aliquet, egestas lectus."
    txt8 = "Donec placerat lacus egestas, aliquam enim vitae, congue ipsum. Praesent vitae eros cursus, pulvinar lectus et, ornare ipsum. Fusce luctus odio vitae hendrerit mollis. Morbi eu turpis vel elit tristique ullamcorper at sodales turpis. Curabitur in ante tincidunt, pellentesque lacus non, dignissim arcu. Mauris ut egestas mi, id elementum ipsum. Morbi justo nisi, laoreet nec lobortis nec, vulputate et justo. Quisque vel pretium quam. Cras consequat quam erat, eu finibus nisi pretium eu. Maecenas ac commodo lacus, non lobortis nunc."
    txt9 = "Vivamus et leo eget turpis scelerisque blandit at vel tellus. Vestibulum ac arcu turpis. Cras iaculis suscipit justo, at cursus ex condimentum non. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Mauris eget tincidunt nisi, at imperdiet orci. Praesent bibendum bibendum nunc sit amet euismod. Nullam eu metus malesuada, faucibus purus eget, imperdiet justo. Donec in dui nunc. Sed vel sodales neque. Duis congue venenatis semper. Donec commodo in magna id tincidunt. Maecenas sollicitudin dignissim lorem id interdum."
    txt10 = "Aliquam eleifend mi arcu, sit amet convallis tellus condimentum sit amet. Duis lobortis nisl lectus, et convallis augue bibendum sit amet. Maecenas vestibulum porta lorem eu pharetra. Aliquam erat volutpat. Pellentesque volutpat nunc sit amet sem vestibulum commodo. In consequat diam id eros tincidunt dignissim. Maecenas aliquam, elit vitae consectetur facilisis, enim lectus facilisis dui, sed sodales leo dui et augue. Phasellus convallis lacinia pellentesque. Mauris et vulputate ligula. Quisque et velit diam. Pellentesque maximus, augue sit amet semper malesuada, urna velit ultrices lorem, et commodo tortor nibh non justo. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas."

    sht1 = "Hello World"
    sht2 = "Buzz"
    sht3 = "The quick brown fox jumps over the lazy dog."

    kb = KeyBindings()
    @kb.add('c-c')
    def _(event):
        " Abort when Control-C has been pressed. "
        event.app.exit(exception=KeyboardInterrupt, style='class:aborting')

    table = [
        [TextArea(sht1), Label(txt2), TextArea(txt1)],
        [Merge(TextArea(sht2), 2), TextArea(txt4)],
        [Button(sht3), Merge(TextArea(txt6), 3)],
        [Button(sht1), TextArea(txt8)],
        [TextArea(sht2), TextArea(txt10)],
    ]

    # table = TextArea(txt2)

    layout = Layout(
        Box(
            Table(
                table=table,
                column_width=D.exact(15),
                column_widths=[None],
                borders=DoubleBorder),
            padding=1,
        ),
    )
    return Application(layout, key_bindings=kb)


if __name__ == '__main__':
    demo().run()
