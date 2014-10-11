from __future__ import unicode_literals

from prompt_toolkit.contrib.regular_languages.grammar import Literal, Variable, Repeat, CharacterSet, Regex
from prompt_toolkit.contrib.regular_languages.compiler import compile, Match, Variables
from prompt_toolkit.contrib.regular_languages.completion import GrammarCompleter
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

import unittest


class GrammarTest(unittest.TestCase):
    def test_simple_match(self):
        grammar = Literal('hello') | Literal('world')
        t = compile(grammar)

        m = t.match('hello')
        self.assertTrue(isinstance(m, Match))

        m = t.match('world')
        self.assertTrue(isinstance(m, Match))

        m = t.match('somethingelse')
        self.assertEqual(m, None)

    def test_variable_varname(self):
        """
        Test `Variable` with varname.
        """
        grammar = Variable(Literal('hello') | Literal('world'), varname='varname') | Literal('test')
        t = compile(grammar)

        m = t.match('hello')
        variables = m.variables()
        self.assertTrue(isinstance(variables, Variables))
        self.assertEqual(variables.get('varname'), 'hello')
        self.assertEqual(variables['varname'], 'hello')

        m = t.match('world')
        variables = m.variables()
        self.assertTrue(isinstance(variables, Variables))
        self.assertEqual(variables.get('varname'), 'world')
        self.assertEqual(variables['varname'], 'world')

        m = t.match('test')
        variables = m.variables()
        self.assertTrue(isinstance(variables, Variables))
        self.assertEqual(variables.get('varname'), None)
        self.assertEqual(variables['varname'], None)

    def test_concatenation(self):
        grammar = Literal('hello') + Literal('world')
        t = compile(grammar)

        m = t.match('helloworld')
        self.assertTrue(isinstance(m, Match))

        m = t.match('hello')
        self.assertEqual(m, None)

    def test_prefix(self):
        """
        Test `match_prefix`.
        """
        grammar = (Literal('hello') + Literal(" ") + Literal('world')) | Literal('something else')
        t = compile(grammar)

        m = t.match_prefix('hello world')
        self.assertTrue(isinstance(m, Match))

        m = t.match_prefix('he')
        self.assertTrue(isinstance(m, Match))

        m = t.match_prefix('')
        self.assertTrue(isinstance(m, Match))

        m = t.match_prefix('som')
        self.assertTrue(isinstance(m, Match))

        m = t.match_prefix('hello wor')
        self.assertTrue(isinstance(m, Match))

        m = t.match_prefix('no-match')
        self.assertEqual(m, None)

        m = t.match_prefix('ello')
        self.assertEqual(m, None)

    def test_something(self):
        """
        Test: '"' + text + '"' grammar.
        """
        grammar = Repeat(CharacterSet(r'\s')) + \
            Variable(Literal('"') + Repeat(CharacterSet('^"')) + Literal('"'), varname='var1') + \
            Repeat(CharacterSet(r'\s'))
        t = compile(grammar)

        # Match full string.
        m = t.match('   "abc" ')
        variables = m.variables()

        self.assertTrue(isinstance(m, Match))
        self.assertEqual(variables.get('var1'), '"abc"')

        m = t.match('"abc"')
        variables = m.variables()

        self.assertTrue(isinstance(m, Match))
        self.assertEqual(variables.get('var1'), '"abc"')

        m = t.match('"ab')
        self.assertEqual(m, None)

        # Prefix matching.
        m = t.match_prefix('"ab')
        self.assertTrue(isinstance(m, Match))

        m = t.match_prefix('  "ab')
        self.assertTrue(isinstance(m, Match))

    def test_complter(self):
        class completer1(Completer):
            def get_completions(self, document):
                yield Completion('before-%s-after' % document.text, -len(document.text))
                yield Completion('before-%s-after-B' % document.text, -len(document.text))

        class completer2(Completer):
            def get_completions(self, document):
                yield Completion('before2-%s-after2' % document.text, -len(document.text))
                yield Completion('before2-%s-after2-B' % document.text, -len(document.text))

        # Create grammar.  "var1" + "whitespace" + "var2"
        v1 = Variable(Repeat(CharacterSet('a-z')), varname='var1', completer=completer1())
        v2 = Variable(Repeat(CharacterSet('a-z')), varname='var2', completer=completer2())
        grammar = v1 + Regex('\\s+') + v2
        t = compile(grammar)

        # Test 'get_completions()'
        completer = GrammarCompleter(t)
        completions = list(completer.get_completions(Document('abc def', len('abc def'))))

        self.assertEqual(len(completions), 2)
        self.assertEqual(completions[0].text, 'before2-def-after2')
        self.assertEqual(completions[0].start_position, -3)
        self.assertEqual(completions[1].text, 'before2-def-after2-B')
        self.assertEqual(completions[1].start_position, -3)
