from prompt_toolkit import Application
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import Box, TextArea
# from prompt_toolkit.widgets.base import Border
from prompt_toolkit.layout.containers import Window, VSplit, HSplit, HorizontalAlign, VerticalAlign
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.key_binding.key_bindings import KeyBindings


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


class Table(HSplit):
    def __init__(self, table, column_width="fit", column_widths=[],
                 borders=ThinBorder,
                 window_too_small=None,
                 width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style=''):
        self.column_width = column_width
        self.column_widths = column_widths

        # ensure the table is iterable (has rows)
        if not isinstance(table, list):
            table = [table]

        # detect the maximum number of columns
        columns = []
        for i, row in enumerate(table):
            columns.append(0)

            # ensure the row is iterable (has cells)
            if not isinstance(row, list):
                table[i] = row = [row]

            for j, cell in enumerate(row):
                if isinstance(cell, Merge):
                    pass
                elif isinstance(cell, dict):
                    row[j] = cell = Merge(**cell)
                else:
                    row[j] = cell = Merge(cell)
                columns[-1] += cell.merge
        columns = max(columns)

        children = []
        previous = None
        for row in table:
            children.append(_Border(previous, row, columns, borders))
            children.append(_Row(row, self, columns, borders))
            previous = row
        children.append(_Border(previous, None, columns, borders))

        super().__init__(
            children=children, window_too_small=window_too_small,
            width=width, height=height, z_index=z_index,
            modal=modal, key_bindings=key_bindings, style=style)


class _Row(VSplit):
    def __init__(self, row, table, columns, borders,
                 window_too_small=None, align=HorizontalAlign.JUSTIFY,
                 padding=Dimension.exact(0), padding_char=None,
                 padding_style='', width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style=''):
        self.table = table

        children = []
        c = 0
        for cell in row:
            children.append(Window(width=1, char=borders.VERTICAL))
            children.append(_Cell(cell.cell, table, self))
            c += cell.merge
        for c in range(columns - c):
            children.append(Window(width=1, char=borders.VERTICAL))
            children.append(_Cell(TextArea(), table, self))
        children.append(Window(width=1, char=borders.VERTICAL))

        super().__init__(
            children=children, window_too_small=window_too_small, align=align,
            padding=padding, padding_char=padding_char,
            padding_style=padding_style, width=width, height=height,
            z_index=z_index, modal=modal, key_bindings=key_bindings,
            style=style)


class _Border(VSplit):
    def __init__(self, previous, next, columns, borders,
                 window_too_small=None, align=HorizontalAlign.JUSTIFY,
                 padding=Dimension.exact(0), padding_char=None,
                 padding_style='', width=None, height=None, z_index=None,
                 modal=False, key_bindings=None, style=''):
        self.previous = previous
        self.next = next

        if previous:
            tmp = []
            for child in previous:
                tmp.extend([False] * (child.merge - 1))
                tmp.append(True)
            previous_columns = tmp + ([True] * (columns - len(tmp)))
        else:
            previous_columns = [False] * columns

        if next:
            tmp = []
            for child in next:
                tmp.extend([False] * (child.merge - 1))
                tmp.append(True)
            next_columns = tmp + ([True] * (columns - len(tmp)))
        else:
            next_columns = [False] * columns

        children = []
        if previous and next:
            children.append(Window(height=1, width=1, char=borders.LEFT_T))
        elif previous:
            children.append(Window(height=1, width=1, char=borders.BOTTOM_LEFT))
        elif next:
            children.append(Window(height=1, width=1, char=borders.TOP_LEFT))
        for c in range(columns):
            children.append(Window(height=1, char=borders.HORIZONTAL))

            if previous_columns[c] and next_columns[c]:
                char = borders.INTERSECT
            elif previous_columns[c]:
                char = borders.BOTTOM_T
            elif next_columns[c]:
                char = borders.TOP_T
            else:
                char = borders.HORIZONTAL
            children.append(Window(height=1, width=1, char=char))
        children.pop()
        if previous and next:
            children.append(Window(height=1, width=1, char=borders.RIGHT_T))
        elif previous:
            children.append(Window(height=1, width=1, char=borders.BOTTOM_RIGHT))
        elif next:
            children.append(Window(height=1, width=1, char=borders.TOP_RIGHT))

        height = 1

        super().__init__(
            children=children, window_too_small=window_too_small, align=align,
            padding=padding, padding_char=padding_char,
            padding_style=padding_style, width=width, height=height,
            z_index=z_index, modal=modal, key_bindings=key_bindings,
            style=style)


class _Cell(Box):
    def __init__(self, cell, table, row,
                 padding=0,
                 padding_left=None, padding_right=None,
                 padding_top=None, padding_bottom=None,
                 width=None, height=None,
                 style='', char=None, modal=False, key_bindings=None):
        self.table = table
        self.row = row

        body = cell

        super().__init__(
            body=body, padding=padding,
            padding_left=padding_left, padding_right=padding_right,
            padding_top=padding_top, padding_bottom=padding_bottom,
            width=width, height=height,
            style=style, char=char, modal=modal, key_bindings=key_bindings)


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

    table = [
        [TextArea(sht1), TextArea(txt2), TextArea(txt1)],
        [Merge(TextArea(sht2), 2), TextArea(txt4)],
        [TextArea(sht3), Merge(TextArea(txt6), 3)],
        [TextArea(sht1), TextArea(txt8)],
        [TextArea(sht2), TextArea(txt10)],
    ]

    # table = TextArea(sht1)

    kb = KeyBindings()
    @kb.add('c-c')
    def _(event):
        " Abort when Control-C has been pressed. "
        event.app.exit(exception=KeyboardInterrupt, style='class:aborting')

    layout = Layout(
        Box(
            Table(table),
            padding=1,
        ),
    )
    app = Application(layout, key_bindings=kb)
    app.run()
