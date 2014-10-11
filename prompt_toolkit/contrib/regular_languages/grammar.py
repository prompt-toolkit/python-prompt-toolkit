"""
Grammar for defining a regular language.
See what a regular language is: http://en.wikipedia.org/wiki/Regular_language
"""
from __future__ import unicode_literals
from prompt_toolkit.completion import Completer
from prompt_toolkit.validation import Validator

import re

__all__ = (
    'Repeat',
    'Variable',
    'Regex',

    # Utils
    'Literal',
    'Repeat1',
    'CharacterSet',
)


class Node(object):
    """
    Base class for all the grammar nodes.
    (You don't initialize this one.)
    """
    def __add__(self, other_node):
        return Sequence([self, other_node])

    def __or__(self, other_node):
        return Any([self, other_node])


class Any(Node):
    """
    Union operation (OR operation) between several grammars. You don't
    initialize this yourself, but it's a result of a "Grammar1 | Grammar2"
    operation.
    """
    def __init__(self, children):
        self.children = children

    def __or__(self, other_node):
        return Any(self.children + [other_node])

    def __repr__(self):
        return 'Any(len=%r)' % len(self.children)


class Sequence(Node):
    """
    Concatenation operation of several grammars. You don't initialize this
    yourself, but it's a result of a "Grammar1 + Grammar2" operation.
    """
    def __init__(self, children):
        self.children = children

    def __add__(self, other_node):
        return Sequence(self.children + [other_node])

    def __repr__(self):
        return 'Sequence(len=%r)' % len(self.children)


class Regex(Node):
    """
    Regular expression.

    Important:
    - Prefer wrapping in Repeat() instead of using '*'. (The latter does not always work.)
    - Don't use (...)-grouping, instead use (?:...).
    """
    def __init__(self, regex):
        self.regex = regex

        # Try to compile. This should be a valid regex, even if it will be
        # placed inside another regex.
        re.compile(regex)

    def as_regex(self):
        return self.regex


class Variable(Node):  # TODO: document better. especially the variables, completer, etc...
    """
    Mark a variable in the regular grammar. This will be translated into a
    named group. Each variable can have his own completer, validator, etc..

    :param childnode: The grammar which is wrapped inside this variable.
    :param varname: String.
    :param completer: A callable which contains the complete function for this group.
    """
    def __init__(self, childnode, varname=None, completer=None, wrapper=None, unwrapper=None,
                 token=None, lexer=None, validator=None):
        assert completer is None or isinstance(completer, Completer)
        assert validator is None or isinstance(validator, Validator)

        self.childnode = childnode
        self.varname = varname
        self.completer = completer
        self.wrapper = wrapper or (lambda text: text)
        self.unwrapper = unwrapper or (lambda text: text)
        self.validator = validator
        self.token = token

        if lexer:
            self.lexer = lexer(
                stripnl=False,
                stripall=False,
                ensurenl=False)
        else:
            self.lexer = None

    def __repr__(self):
        return 'Variable(childnode=%r, varname=%r)' % (self.childnode, self.varname)

    def unwrap(self, text):
        if self.unwrapper:
            return self.unwrapper(text)
        else:
            return text

    def wrap(self, text):
        if self.wrapper:
            return self.wrapper(text)
        else:
            return text


class Repeat(Node):
    def __init__(self, childnode, min_repeat=0, max_repeat=None):
        self.childnode = childnode
        self.min_repeat = min_repeat
        self.max_repeat = max_repeat

    def __repr__(self):
        return 'Repeat(childnode=%r)' % (self.childnode, )


# Utils


class CharacterSet(Regex):
    """
    A regex character set.

    :param data: String to be wrapped inside square brackets. e.g. 'a-z'
    :param negate: Boolean.
    """
    def __init__(self, data, negate=False):
        self.data = data
        self.negate = negate

        super(CharacterSet, self).__init__(self._re())

    def _re(self):
        """ Return regex character class. """
        if self.negate:
            return '[^%s]' % self.data
        else:
            return '[%s]' % self.data

    def __repr__(self):
        if self.negate:
            return 'CharacterSet(%r, negate=True)' % (self.data, )
        else:
            return 'CharacterSet(%r)' % (self.data, )


def Literal(text):
    """
    String of characters.
    """
    characters = [CharacterSet(re.escape(c)) for c in text]
    return Sequence(characters)


class Repeat1(Repeat):
    def __init__(self, childnode, max_repeat=None):
        super(Repeat1, self).__init__(childnode, min_repeat=1, max_repeat=max_repeat)
