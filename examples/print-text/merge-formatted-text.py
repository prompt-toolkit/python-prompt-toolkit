#!/usr/bin/env python
"""
Demonstration of string concatenation with ``merge_formatted_text``.
"""
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import ANSI, HTML, merge_formatted_text


def main():
    html = HTML("<u><ansired>Hello</ansired></u> ")
    ansi = ANSI("\x1b[32mworld\n")

    merged_text = merge_formatted_text([html, ansi])

    print_formatted_text(merged_text)


if __name__ == "__main__":
    main()
