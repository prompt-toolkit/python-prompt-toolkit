"""
Tool for expressing the grammar of an input as a regular language.

Example:

    # Create and compile a simple grammar.
    v1 = Variable(Repeat(Regex('[a-z]')), varname='var1', completer=completer1)
    v2 = Variable(Repeat(Regex('[a-z]')), varname='var2', completer=completer2)
    grammar = v1 + Repeat(Regex('[\\s]')) + v2
    g = compile(grammar)

    # Now match a prefix of this grammar. (input at the command line, before cursor position.)
"""
