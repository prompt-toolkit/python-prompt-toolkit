#!/usr/bin/env python
"""
Example of nested autocompletion with meta.
"""
from prompt_toolkit import prompt
from prompt_toolkit.completion.nested_meta import NestedMetaCompleter, NestedMetaData

completer = NestedMetaCompleter(
    [
        NestedMetaData(
            "show",
            "some show help",
            [
                NestedMetaCompleter(
                    [NestedMetaData("version", "show version meta", [])]
                ),
                NestedMetaCompleter(
                    [NestedMetaData("clock", "[beta] show clock meta", [])]
                ),
                NestedMetaCompleter(
                    [
                        NestedMetaData(
                            "ip",
                            "show ip meta",
                            [
                                NestedMetaCompleter(
                                    [
                                        NestedMetaData(
                                            "interfaces",
                                            "interfaces meta",
                                            [
                                                NestedMetaCompleter(
                                                    [
                                                        NestedMetaData(
                                                            "brief", "brief meta", []
                                                        )
                                                    ]
                                                ),
                                            ],
                                        )
                                    ]
                                ),
                            ],
                        )
                    ]
                ),
            ],
        ),
        NestedMetaData("exit", "now", []),
    ]
)


def main():
    text = prompt("Type a command: ", completer=completer)
    print("You said: %s" % text)


if __name__ == "__main__":
    main()
