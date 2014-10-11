"""
Compiler for a regular grammar.
"""
from __future__ import unicode_literals
import re

from .grammar import Any, Sequence, Regex, Variable, Repeat

__all__ = (
    'compile',
)


class _CompiledGrammar(object):
    """
    Compiles a grammar. This will prepare some regular expressions matching
    this grammar.
    """
    def __init__(self, root_node):
        self.root_node = root_node

        #: Dictionary that will map the redex names to Node instances.
        self._group_names_to_nodes = {}
        counter = [0]

        def create_group_func(node):
            name = 'n%s' % counter[0]
            self._group_names_to_nodes[name] = node
            counter[0] += 1
            return name

        # Compile regex strings.
        self._re_pattern = '^%s$' % self._transform(root_node, create_group_func)
        self._re_prefix_patterns = list(self._transform_prefix(root_node, create_group_func))

        # Compile the regex itself.
        self._re = re.compile(self._re_pattern)
        self._re_prefix = [re.compile(t) for t in self._re_prefix_patterns]

    @classmethod
    def _transform(cls, root_node, create_group_func):
        """
        Turn a :class:`Node` object into a regular expression.

        :param root_node: The :class:`Node` instance for which we generate the grammar.
        :param create_group_func: A callable which takes a `Node` and returns the next
            free name for this node.
        """
        def transform(node):
            # Turn `Any` into an OR.
            if isinstance(node, Any):
                return '(?:%s)' % '|'.join(transform(c) for c in node.children)

            # Concatenate a `Sequence`
            elif isinstance(node, Sequence):
                return ''.join(transform(c) for c in node.children)

            # A character is a literal. (Escaping happens in the `Regex` itself.
            elif isinstance(node, Regex):
                return node.as_regex()

            # A `Variable` wraps the children into a named group.
            elif isinstance(node, Variable):
                return '(?P<%s>%s)' % (create_group_func(node), transform(node.childnode))

            # `Repeat`.
            elif isinstance(node, Repeat):
                return '(?:%s){%i,%s}' % (
                    transform(node.childnode), node.min_repeat,
                    ('' if node.max_repeat is None else str(node.max_repeat)))

            else:
                raise TypeError('Got %r' % node)

        return transform(root_node)

    @classmethod
    def _transform_prefix(cls, root_node, create_group_func):
        """
        Yield all the regular expressions matching a prefix of the grammar
        defined by the `Node` instance.

        This can yield multiple expressions, because in the case of on OR
        operation in the grammar, we can have another outcome depending on
        which clause would appear first. E.g. "(A|B)C" is not the same as
        "(B|A)C" because the regex engine is lazy and takes the first match.
        However, because we the current input is actually a prefix of the
        grammar which meight not yet contain the data for "C", we need to know
        both intermediate states, in order to call the appropriate
        autocompletion for both cases.

        :param root_node: The :class:`Node` instance for which we generate the grammar.
        :param create_group_func: A callable which takes a `Node` and returns the next
            free name for this node.
        """
        def transform(node):
            # Generate regexes for all permutations of this OR. Each node
            # should be in front once.
            if isinstance(node, Any):
                for c in node.children:
                    for r in transform(c):
                        yield '(?:%s)?' % r

            # For a sequence. We can either have a match for the sequence
            # of all the children, or for an exact match of the first X
            # children, followed by a partial match of the next children.
            elif isinstance(node, Sequence):
                for i in range(len(node.children)):
                    a = [cls._transform(c, create_group_func) for c in node.children[:i]]
                    for c in transform(node.children[i]):
                        yield '(?:%s)' % (''.join(a) + c)

            elif isinstance(node, Regex):
                yield '(?:%s)?' % node.as_regex()

            elif isinstance(node, Variable):
                # (Note that we should not append a '?' here. the 'transform'
                # method will already recursively do that.)
                for c in transform(node.childnode):
                    yield '(?P<%s>%s)' % (create_group_func(node), c)

            elif isinstance(node, Repeat):
                # If we have a repetition of 8 times. That would mean that the
                # current input could have for instance 7 times a complete
                # match, followed by a partial match.
                prefix = cls._transform(node.childnode, create_group_func)

                for c in transform(node.childnode):
                    if node.max_repeat:
                        repeat_sign = '{,%i}' % (node.max_repeat - 1)
                    else:
                        repeat_sign = '*'
                    yield '(?:%s)%s(?:%s)?' % (prefix, repeat_sign, c)

            else:
                raise TypeError('Got %r' % node)

        for r in transform(root_node):
            yield '^%s$' % r

    def match(self, string):
        """
        Match the string with the grammar.
        Returns a :class:`Match` instance.

        :param string: The input string.
        """
        m = self._re.match(string)

        if m:
            return Match(string, [(self._re, m)], self._group_names_to_nodes)

    def match_prefix(self, string):
        """
        Do a partial match of the string with the grammar. The returned
        :class:`Match` instance can contain multiple representations of the
        match.

        :param string: The input string.
        """
        matches = [(r, r.match(string)) for r in self._re_prefix]
        matches = [(r, m) for r, m in matches if m]

        if matches != []:
            return Match(string, matches, self._group_names_to_nodes)


def compile(root_node):
    """
    Compile grammar, returning a `CompiledGrammar` instance.
    """
    return _CompiledGrammar(root_node)


class Match(object):
    """
    :param string: The input string.
    :param re_matches: List of (compiled_re_pattern, re_match) tuples.
    :param group_names_to_nodes: Dictionary mapping all the re group names to the matching Node instances.
    """
    def __init__(self, string, re_matches, group_names_to_nodes):
        self.string = string
        self._re_matches = re_matches
        self._group_names_to_nodes = group_names_to_nodes

    def _nodes_to_regs(self):
        """
        Return a list of (Node, reg) tuples.
        """
        def get_tuples():
            for r, re_match in self._re_matches:
                for group_name, group_index in r.groupindex.items():
                    reg = re_match.regs[group_index]
                    node = self._group_names_to_nodes[group_name]
                    yield (node, reg)

        return list(get_tuples())

    def _nodes_to_values(self):
        """
        Returns list of list of (Node, string_value) tuples.
        """
        def is_none(slice):
            return slice[0] == -1 and slice[1] == -1

        def get(slice):
            return self.string[slice[0]:slice[1]]

        return [(node, get(slice), slice) for node, slice in self._nodes_to_regs() if not is_none(slice)]

    def variables(self):
        """
        Returns :class:`Variables` instance.
        """
        return Variables([(k, k.unwrap(v), sl) for k, v, sl in self._nodes_to_values() if isinstance(k, Variable)])

    def end_nodes(self):
        """
        Return (Node, start, stop) tuples for all the nodes having their end
        position at the end of the input string.
        """
        for node, reg in self._nodes_to_regs():
            # If this part goes until the end of the input string.
            if reg[1] == len(self.string):
                yield (node, reg[0], reg[1])


class Variables(object):
    def __init__(self, tuples):
        #: List of (node, value, slice) tuples.
        self._tuples = tuples

    def __repr__(self):
        return 'Variables(%s)' % ', '.join('%s=%r' % (k.varname, v) for k, v, _ in self._tuples)

    def get(self, key, default=None):
        items = self.getall(key)
        return items[0] if items else default

    def getall(self, key):
        return [v for k, v, _ in self._tuples if k.varname == key]

    def __getitem__(self, key):
        return self.get(key)

    def __iter__(self):
        """
        Yield `MatchVariable` instances.
        """
        for node, value, slice in self._tuples:
            yield MatchVariable(node, value, slice)


class MatchVariable(object):
    def __init__(self, node, value, slice):
        self.node = node
        self.value = value
        self.slice = slice

        self.start = self.slice[0]
        self.stop = self.slice[1]
