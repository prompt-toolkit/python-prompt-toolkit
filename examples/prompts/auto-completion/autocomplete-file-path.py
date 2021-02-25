import pathlib
import re
from typing import Iterable

from prompt_toolkit import prompt
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

_FILE_PATH_RE = re.compile(r"[^\s\"'\t]+")


class PathCompleter(Completer):
    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        path = document.get_word_before_cursor(pattern=_FILE_PATH_RE)

        # absoulte path
        if path.startswith("/"):
            search_path_str = "/"
            file_substr = path[1:]
        # sub path
        elif "/" in path:
            search_path_str, file_substr = path.rsplit("/", maxsplit=1)
            search_path_str += "/"
        # current path
        else:
            search_path_str = ""
            file_substr = path

        search_path = pathlib.Path(search_path_str)

        # directory doesnt even exist
        if not search_path.exists():
            return

        # NOTE: currently doesnt work with filepaths with spaces. Other non-ascii characters may also break it.
        for sub_path in search_path.glob(f"{file_substr}*"):
            yield Completion(sub_path.as_posix(), start_position=-len(path))



def main():
    text = prompt(
        "shell: ",
        completer=PathCompleter(),
        complete_while_typing=False,
    )
    print("You said: %s" % text)


if __name__ == "__main__":
    main()
