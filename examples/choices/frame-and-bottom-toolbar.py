from __future__ import annotations

from prompt_toolkit.filters import is_done
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.styles import Style


def main() -> None:
    style = Style.from_dict(
        {
            "frame.border": "#ff4444",
            "selected-option": "bold",
            # We use 'noreverse' because the default style for 'bottom-toolbar'
            # uses 'reverse'.
            "bottom-toolbar": "#ffffff bg:#333333 noreverse",
        }
    )

    result = choice(
        message=HTML("<u>Please select a dish</u>:"),
        options=[
            ("pizza", "Pizza with mushrooms"),
            ("salad", "Salad with tomatoes"),
            ("sushi", "Sushi"),
        ],
        style=style,
        bottom_toolbar=HTML(
            " Press <b>[Up]</b>/<b>[Down]</b> to select, <b>[Enter]</b> to accept."
        ),
        # Use `~is_done`, if you only want to show the frame while editing and
        # hide it when the input is accepted.
        # Use `True`, if you always want to show the frame.
        show_frame=~is_done,
    )
    print(result)


if __name__ == "__main__":
    main()
