from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter


def main():
    text = prompt(
        "shell: ",
        completer=PathCompleter(use_word=True),
        complete_while_typing=False,
    )
    print("You said: %s" % text)


if __name__ == "__main__":
    main()
