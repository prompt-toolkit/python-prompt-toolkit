#!/usr/bin/env python
from rich.markdown import Markdown
from rich.text import Text

from prompt_toolkit import choice
from prompt_toolkit.formatted_text.rich import Rich

# For the header, we wrap the `Markdown` object from `rich` in a `Rich` object
# from `prompt_toolkit`, so that we can explicitly set a width.
header = Rich(
    Markdown(
        """
# Please select a dish

Choose *one* item please.

```python
def some_example_function() -> None: "test"
```
""".strip()
    ),
    width=50,
    style="black on blue",
)


def main():
    answer = choice(
        message=header,
        options=[
            ("pizza", "Pizza with mushrooms"),
            (
                "salad",
                Text.from_markup(
                    ":warning: [green]Salad[/green] with [red]tomatoes[/red]"
                ),
            ),
            ("sushi", "Sushi"),
        ],
        show_frame=True,
    )
    print(f"You said: {answer}")


if __name__ == "__main__":
    main()
