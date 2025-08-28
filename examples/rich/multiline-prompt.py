#!/usr/bin/env python
from rich.markdown import Markdown

from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import merge_formatted_text
from prompt_toolkit.formatted_text.rich import Rich

# For the header, we wrap the `Markdown` object from `rich` in a `Rich` object
# from `prompt_toolkit`, so that we can explicitly set a width.
header = Rich(
    Markdown(
        """
# Type the name of the following function:

```python
def fibonacci(number: int) -> int:
    "compute Fibonacci number"
```

"""
    ),
    width=50,
)


def main():
    answer = prompt(merge_formatted_text([header, "> "]))
    print(f"You said: {answer}")


if __name__ == "__main__":
    main()
