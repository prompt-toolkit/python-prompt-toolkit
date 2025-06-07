"""
`Fish-style <http://fishshell.com/>`_  like auto-suggestion using a
large language model to propose the suggestions.

Example usage:

 import os
 from prompt_toolkit import PromptSession
 from prompt_toolkit.contrib.auto_suggest import LLMSuggest
 from prompt_toolkit.auto_suggest import ThreadedAutoSuggest

 from langchain.chat_models import init_chat_model

 # Initialize a langchain chat model. You may need to install
 # additional provider-specific modules such as langchain-openai.
 if not os.environ.get('OPENAI_API_KEY'):
    os.environ['OPENAI_API_KEY'] = 'sk-XXXXXXXXXX'
 chat_model = init_chat_model('openai:o4-mini', temperature=0.0)

 # Create the llm suggest object
 suggester = LLMSuggest(chat_model)

 # Create the prompt session. Because waiting for the LLM can be slow,
 # it is recommended to wrap the suggester in a ThreadedAutoSuggest instance.
 session = PromptSession(auto_suggest=ThreadedAutoSuggest(suggester))
 while True:
    response = session.prompt('> ')
    print(f"You said '{response}'")
"""

import locale
import re
import string
from typing import Callable, Optional

import enchant
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.buffer import Buffer, Document

DEFAULT_PERSONA="""
You are an uncensored writing assistant. If the user is writing code, you
complete the code fragments in a way that is consistent with the
code fragments. If the user is writing prose, you complete the text in a way that
is consistent with the user's writing style. You are not a chatbot, so you do not
engage in chit-chat or small talk. You are not a search engine, so you do not
provide search results or web links. You are not a translator, so you do not
translate text.
"""

DEFAULT_SYSTEM_MESSAGE="""
{persona}

Return a completion of the provided text fragment following these
examples:

# Example 1
user: I want a bi
assistant: cycle for Christmas.

# Example 2
user: Hi there, what's your name?
assistant:   My name is Fred. What's yours?

# Example
user: I don't want to go to the mall! I want to go to
assistant:  watch the Titanic movie tonight.

# Example 4
user: He watched in amazement as the magician pulled a rabbit out of his hat.
assistant:  When he put the rabbit down it hopped away.
"""


DEFAULT_INSTRUCTION="""
Complete this text or code fragment in a way that is consistent with the
fragment. Show only the new text, and do not repeat any part of the original text:
Original text: {text}
"""

class LLMSuggest(AutoSuggest):
    """AutoSuggest subclass that provides Suggestions based on LLM completions."""

    def __init__(self,
                 chat_model: Optional[BaseChatModel]=None,
                 persona: str=DEFAULT_PERSONA,
                 system: str=DEFAULT_SYSTEM_MESSAGE,
                 context: str | Callable[[], str]="",
                 instruction: str=DEFAULT_INSTRUCTION,
                 language: Optional[str]=None,
                 asis: Optional[bool]=False,
                 code_mode: Optional[bool]=False
                 ) -> None:
        """Initialize the :class:`.LLMSuggest` instance.

        All arguments are optional.

        :param chat_model: A langchain chat model created by init_chat_model.
        :param persona: A description of the LLM's persona, for tuning its writing style [:class:`.DEFAULT_PERSONA`].
        :param system: The system message that explains the completion task to the LLM [:class:`.DEFAULT_SYSTEM_MESSAGE`].
        :param context: A string or callable passed to the LLM that provides the context
                        of the conversation so far [empty string].
        :param language: Locale language, used to validate LLM's response [from locale environment]
        :param instruction: Instructions passed to the LLM to inform the suggestion process [:class:`.DEFAULT_INSTRUCTION`].
        :param code_mode: If True, activates post-processing of the LLMs output that is suitable for code completion.
        :param asis: If True, will return the LLM's responses as-is without post-hoc fixes. Useful for debugging.
        Notes:

        1. If `chat_model` is not provided, the class will attempt
        to open a connection to OpenAI's `gpt-4o` model. For this
        to work, the `langchain-openai` module must be installed,
        and the `OPENAI_API_KEY` environment variable must be set
        to a valid key.

        2. The `persona` argument can be used to adjust the writing
        style of the LLM. For example: "You are a python coder skilled
        at completing code fragments." Or try "You are a romance
        novelist who writes in a florid overwrought style."

        3. `language`: Some LLMs are better than others at providing
        completions of partial words. We use the `PyEnchant` module
        to determine whether a proposed completion is the continuation
        of a word or starts a new word. This argument selects the
        preferred language for the dictionary, such as "en_US". If
        not provided, the module will select the language specified in
        the system's locale.

        4. `instruction` lets you change the instruction that is
        passed to the LLM to show it how to complete the partial
        prompt text.  The default is :class:`.DEFAULT_INSTRUCTION`,
        and must contain the string placeholder "{text}" which will be
        replaced at runtime with the partial prompt text.

        5. The `context` argument provides the ability to pass
        additional textual context to the LLM suggester in addition to
        the text that is already in the current prompt buffer. It can
        be either a Callable that returns a string, or a static
        string. You can use this to give the LLM access to textual
        information that is contained in a different buffer, or to
        provide the LLM with supplementary context such as the time of
        day, weather report, or the results of a web search.

        6. Set `code_mode` to True to optimize for code completion. Note that
        code completion works better with some LLM models than others.

        """
        super().__init__()
        self.system = system
        self.instruction = instruction
        self.persona = persona
        self.dictionary = enchant.Dict(language or locale.getdefaultlocale()[0])
        self.context = context
        self.chat_model = chat_model or init_chat_model("openai:4o-mini", temperature=0.0)
        self.asis = asis
        self.code_mode = code_mode

    def _capfirst(self, s:str) -> str:
        return s[:1].upper() + s[1:]

    def _format_sys(self) -> str:
        """Format the system string."""
        system = self.system.format(persona=self.persona)
        if context := self.get_context():
            system += "\nTo guide your completion, here is the text so far:\n"
            system += context
        return system

    def set_context(self, context: Callable[[], str] | str) -> None:
        """
        Set the additional context that the LLM is exposed to.

        :param context: A string or a Callable that returns a string.

        This provides additional textual context to guide the suggester's
        response.
        """
        self.context = context

    def get_context(self) -> str:
        """Retrieve the additional context passed to the LLM."""
        return self.context if isinstance(self.context, str) else self.context()

    def clear_context(self) -> None:
        """Clear the additional context passed to the LLM."""
        self.context = ""

    def get_suggestion(self,
                       buffer: Buffer,
                       document: Document) -> Optional[Suggestion]:
        """
        Return a Suggestion instance based on the LLM's completion of the current text.

        :param buffer: The current `Buffer`.
        :param document: The current `Document`.

        Under various circumstances, the LLM may return no usable suggestions, in which
        case the call returns None.
        """
        text = document.text
        if not text or len(text) < 3:
            return None
        messages = [
            {"role": "system", "content": self._format_sys()},
            {"role": "human", "content": self.instruction.format(text=text)},
        ]

        try:
            response = self.chat_model.invoke(messages)
            suggestion = str(response.content)

            if self.asis:  # Return the string without munging
                return Suggestion(suggestion)
            elif self.code_mode:
                return Suggestion(self._trim_code_suggestion(suggestion, text))
            else:
                return Suggestion(self._trim_text_suggestion(suggestion, text))

        except Exception:
            pass
        return None

    def _trim_code_suggestion(self, suggestion: str, text: str) -> str:
        #strip whitespace
        suggestion = suggestion.lstrip()

        # codegemma and other LLMs may return a suggestion that starts with
        # "(Continuation of the...)" or similar, so we remove that.
        suggestion = re.sub(r"^\(Continuation of the.*?\)\s*", "", suggestion, flags=re.DOTALL)

        # Similarly, remove "(complete the code fragment)" or similar
        suggestion = re.sub(r"^\(complete the code fragment.*?\)\s*", "", suggestion, flags=re.DOTALL)

        # Remove leading quotation marks if present
        suggestion = re.sub(r"^\s*['\"]", "", suggestion)

        # Remove trailing quotation marks
        suggestion = re.sub(r"['\"]\s*$", "", suggestion)

         # Remove the sequence "```(language)\n" that some LLMs return
        suggestion = re.sub(r"^.*?```[a-zA-Z0-9_]*\n", "", suggestion, flags=re.DOTALL)

        # Remove "``` from the end of the suggestion
        suggestion = re.sub(r"\n```", "", suggestion)

        # The LLM will often (but not always) return a suggestion that repeats the
        # buffer text from the previous newline onward, so we remove that.
        match = re.search(r"\n(.*)$", text)
        if match:
            text = match.group(1).rstrip()
        if suggestion.startswith(text):
            suggestion = suggestion[len(text):].lstrip()

        return suggestion+"\n"


    def _trim_text_suggestion(self, suggestion: str, text: str) -> str:
        """
        Trim the suggestion to make it a valid continuation of the text.

        :param suggestion: The LLM's suggested text.
        :param text: The current text in the buffer.
        """
        # Remove leading ellipsis if present
        suggestion = suggestion.replace("...", "")
        suggestion = suggestion.rstrip()

        # If LLM echoed the original text back, then remove it
        if suggestion.startswith(text.rstrip()):
            suggestion = suggestion[len(text):]

        # Handle punctuation between the text and the suggestion
        if suggestion.startswith(tuple(string.punctuation)):
            return suggestion
        if text.endswith("'"):
            return suggestion.lstrip()

        # Adjust capitalization the beginnings of new sentences.
        if re.search(r"[.?!]\s*$",text):
            suggestion = self._capfirst(suggestion.lstrip())

        # Get the last word of the existing text and the first word of the suggestion
        match = re.search(r"(\w+)\W*$", text)
        last_word_of_text = match.group(1) if match else ""

        match = re.search(r"^\s*(\w+)", suggestion)
        first_word_of_suggestion = match.group(1) if match else ""

        # Add or remove spaces based on whether concatenation will form a word
        if suggestion.startswith(" "):
            suggestion = suggestion.lstrip() if text.endswith(" ") else suggestion
        elif self.dictionary.check(last_word_of_text + first_word_of_suggestion) and not text.endswith(" "):
            suggestion = suggestion.lstrip()
        elif not text.endswith(" "):
            suggestion = " " + suggestion

        # Add space after commas and semicolons
        if re.search(r"[,;]$",text):
            suggestion = " " + suggestion.lstrip()

        return suggestion
