"""
Validator for a regular langage.
"""
from __future__ import unicode_literals

from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.document import Document

from .compiler import _CompiledGrammar

__all__ = (
    'GrammarValidator',
)


class GrammarValidator(Validator):
    """
    This validator processes all the validators that are passed to the
    variables of the grammar.
    """
    def __init__(self, compiled_grammar):
        assert isinstance(compiled_grammar, _CompiledGrammar)
        self.compiled_grammar = compiled_grammar

    def validate(self, document):
        m = self.compiled_grammar.match_prefix(document.text)

        if m:
            for v in m.variables():
                if v.node.validator:
                    # Unwrap text.
                    unwrapped_text = v.node.unwrapper(v.value)

                    # Create a document, for the completions API (text/cursor_position)
                    inner_document = Document(unwrapped_text, len(unwrapped_text))

                    try:
                        v.node.validator.validate(inner_document)
                    except ValidationError as e:
                        raise ValidationError(
                            index=v.start + e.index,
                            message=e.message)
