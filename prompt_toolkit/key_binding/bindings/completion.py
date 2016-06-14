"""
Key binding handlers for displaying completions.
"""
from __future__ import unicode_literals
from prompt_toolkit.completion import CompleteEvent, get_common_complete_suffix
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.keys import Keys
from prompt_toolkit.key_binding.registry import Registry

import math

__all__ = (
    'generate_completions',
    'display_completions_like_readline',
)

def generate_completions(event):
    r"""
    Tab-completion: where the first tab completes the common suffix and the
    second tab lists all the completions.
    """
    b = event.current_buffer

    def second_tab():
        if b.complete_state:
            b.complete_next()
        else:
            event.cli.start_completion(select_first=True)

    # On the second tab-press, or when already navigating through
    # completions.
    if event.is_repeat or b.complete_state:
        second_tab()
    else:
        event.cli.start_completion(insert_common_part=True,
                                   select_first=True)


def display_completions_like_readline(event):
    """
    Key binding handler for readline-style tab completion.
    This is meant to be as similar as possible to the way how readline displays
    completions.

    Generate the completions immediately (blocking) and display them above the
    prompt in columns.

    Usage::

        # Call this handler when 'Tab' has been pressed.
        registry.add_binding(Keys.ControlI)(display_completions_like_readline)
    """
    # Request completions.
    b = event.current_buffer
    if b.completer is None:
        return
    complete_event = CompleteEvent(completion_requested=True)
    completions = list(b.completer.get_completions(b.document, complete_event))

    # Calculate the common suffix.
    common_suffix = get_common_complete_suffix(b.document, completions)

    # One completion: insert it.
    if len(completions) == 1:
        b.delete_before_cursor(-completions[0].start_position)
        b.insert_text(completions[0].text)
    # Multiple completions with common part.
    elif common_suffix:
        b.insert_text(common_suffix)
    # Otherwise: display all completions.
    elif completions:
        _display_completions_like_readline(event.cli, completions)


def _display_completions_like_readline(cli, completions):
    """
    Display the list of completions in columns above the prompt.
    This will ask for a confirmation if there are too many completions to fit
    on a single page and provide a paginator to walk through them.
    """
    from prompt_toolkit.shortcuts import create_confirm_application
    assert isinstance(completions, list)

    # Get terminal dimensions.
    term_size = cli.output.get_size()
    term_width = term_size.columns
    term_height = term_size.rows

    # Calculate amount of required columns/rows for displaying the
    # completions. (Keep in mind that completions are displayed
    # alphabetically column-wise.)
    max_compl_width = min(term_width,
        max(get_cwidth(c.text) for c in completions) + 1)
    column_count = max(1, term_width // max_compl_width)
    completions_per_page = column_count * (term_height - 1)
    page_count = math.ceil(len(completions) / float(completions_per_page))

    def display(page):
        # Display completions.
        page_completions = completions[page * completions_per_page:
                                       (page+1) * completions_per_page]

        page_row_count = math.ceil(len(page_completions) / float(column_count))
        page_columns = [page_completions[i * page_row_count:(i+1) * page_row_count]
                   for i in range(column_count)]

        result = []
        for r in range(page_row_count):
            for c in range(column_count):
                try:
                    result.append(page_columns[c][r].text.ljust(max_compl_width))
                except IndexError:
                    pass
            result.append('\n')
        cli.output.write(''.join(result))
        cli.output.flush()

    cli.output.write('\n'); cli.output.flush()

    if len(completions) > completions_per_page:
        # Ask confirmation if it doesn't fit on the screen.
        page_counter = [0]
        def display_page(result):
            if result:
                cli.run_in_terminal(lambda: display(page_counter[0]))

                # Display --MORE-- and go to the next page.
                page_counter[0] += 1
                if page_counter[0] < page_count:
                    cli.run_sub_application(
                        _create_more_application(),
                        done_callback=display_page, erase_when_done=True)

        message = 'Display all {} possibilities? (y on n) '.format(len(completions))
        cli.run_sub_application(
            create_confirm_application(message),
            done_callback=display_page, erase_when_done=True)
    else:
        # Display all completions.
        cli.run_in_terminal(lambda: display(0))


def _create_more_application():
    """
    Create an `Application` instance that displays the "--MORE--".
    """
    from prompt_toolkit.shortcuts import create_prompt_application
    registry = Registry()

    @registry.add_binding(' ')
    @registry.add_binding(Keys.ControlJ)
    def _(event):
        event.cli.set_return_value(True)

    @registry.add_binding('n')
    @registry.add_binding('N')
    @registry.add_binding('q')
    @registry.add_binding('Q')
    @registry.add_binding(Keys.ControlC)
    def _(event):
        event.cli.set_return_value(False)

    return create_prompt_application('--MORE--', key_bindings_registry=registry)
