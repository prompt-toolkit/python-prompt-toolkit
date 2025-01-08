#!/usr/bin/env python
"""
A more complex example of a CLI that demonstrates fish-style auto suggestion
across multiple lines.

This can typically be used for LLM that may return multi-line responses.

Note that unlike simple autosuggest, using multiline autosuggest requires more
care as it may shift the buffer layout, and care must taken ton consider the
various case when the number iof suggestions lines is longer than the number of
lines in the buffer, what happens to the existing text (is it pushed down, or
hidden until the suggestion is accepted) Etc.

So generally multiline autosuggest will require a custom processor to handle the
different use case and user experience.

We also have not hooked any keys to accept the suggestion, so it will be up to you
to decide how and when to accept the suggestion, accept it as a whole, like by line, or
token by token.
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import HasFocus, IsDone
from prompt_toolkit.layout.processors import (
    ConditionalProcessor,
    Processor,
    Transformation,
    TransformationInput,
)

universal_declaration_of_human_rights = """
All human beings are born free and equal in dignity and rights.
They are endowed with reason and conscience and should act towards one another
in a spirit of brotherhood
Everyone is entitled to all the rights and freedoms set forth in this
Declaration, without distinction of any kind, such as race, colour, sex,
language, religion, political or other opinion, national or social origin,
property, birth or other status. Furthermore, no distinction shall be made on
the basis of the political, jurisdictional or international status of the
country or territory to which a person belongs, whether it be independent,
trust, non-self-governing or under any other limitation of sovereignty.""".strip().splitlines()


class FakeLLMAutoSuggest(AutoSuggest):
    def get_suggestion(self, buffer, document):
        if document.line_count == 1:
            return Suggestion(" (Add a few new lines to see multiline completion)")
        cursor_line = document.cursor_position_row
        text = document.text.split("\n")[cursor_line]
        if not text.strip():
            return None
        index = None
        for i, l in enumerate(universal_declaration_of_human_rights):
            if l.startswith(text):
                index = i
                break
        if index is None:
            return None
        return Suggestion(
            universal_declaration_of_human_rights[index][len(text) :]
            + "\n"
            + "\n".join(universal_declaration_of_human_rights[index + 1 :])
        )


class AppendMultilineAutoSuggestionInAnyLine(Processor):
    def __init__(self, style: str = "class:auto-suggestion") -> None:
        self.style = style

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        # a convenient noop transformation that does nothing.
        noop = Transformation(fragments=ti.fragments)

        # We get out of the way if the prompt is only one line, and let prompt_toolkit handle the rest.
        if ti.document.line_count == 1:
            return noop

        # first everything before the current line is unchanged.
        if ti.lineno < ti.document.cursor_position_row:
            return noop

        buffer = ti.buffer_control.buffer
        if not buffer.suggestion or not ti.document.is_cursor_at_the_end_of_line:
            return noop

        # compute the number delta between the current cursor line and line we are transforming
        # transformed line can either be suggestions, or an existing line that is shifted.
        delta = ti.lineno - ti.document.cursor_position_row

        # convert the suggestion into a list of lines
        suggestions = buffer.suggestion.text.splitlines()
        if not suggestions:
            return noop

        if delta == 0:
            # append suggestion to current line
            suggestion = suggestions[0]
            return Transformation(fragments=ti.fragments + [(self.style, suggestion)])
        elif delta < len(suggestions):
            # append a line with the nth line of the suggestion
            suggestion = suggestions[delta]
            assert "\n" not in suggestion
            return Transformation([(self.style, suggestion)])
        else:
            # return the line that is by delta-1 suggestion (first suggestion does not shifts)
            shift = ti.lineno - len(suggestions) + 1
            return Transformation(ti.get_line(shift))


def main():
    # Create some history first. (Easy for testing.)

    autosuggest = FakeLLMAutoSuggest()
    # Print help.
    print("This CLI has fish-style auto-suggestion enabled across multiple lines.")
    print("This will try to complete the universal declaration of human rights.")
    print("")
    print("   " + "\n   ".join(universal_declaration_of_human_rights))
    print("")
    print("Add a few new lines to see multiline completion, and start typing.")
    print("Press Control-C to retry. Control-D to exit.")
    print()

    session = PromptSession(
        auto_suggest=autosuggest,
        enable_history_search=False,
        reserve_space_for_menu=5,
        multiline=True,
        prompt_continuation="... ",
        input_processors=[
            ConditionalProcessor(
                processor=AppendMultilineAutoSuggestionInAnyLine(),
                filter=HasFocus(DEFAULT_BUFFER) & ~IsDone(),
            ),
        ],
    )

    while True:
        try:
            text = session.prompt(
                "Say something (Esc-enter : accept, enter : new line): "
            )
        except KeyboardInterrupt:
            pass  # Ctrl-C pressed. Try again.
        else:
            break

    print(f"You said: {text}")


if __name__ == "__main__":
    main()
