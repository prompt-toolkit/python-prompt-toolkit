#!/usr/bin/env python
from pygments.style import Style
from pygments.token import Token

from pyline import CommandLine
from pyline.contrib.shell.code import ShellCode
from pyline.contrib.shell.completers import Path
from pyline.contrib.shell.prompt import ShellPrompt
from pyline.contrib.shell.rules import Any, Sequence, Literal, Repeat, Variable
from pyline.line import Exit


class OurGitCode(ShellCode):
    rule = Any([
            # None: Sequence([ Variable(Path, placeholder='<path>'), Variable(Path, placeholder='<path2>') ]),
            Sequence([
                Any([
                    Literal('cd'),
                    Literal('rm'),
                    Literal('ls'),
                    ]),
                    Variable(Path, placeholder='<directory>') ]),
          #  Sequence([Literal('rm'), Variable(Path, placeholder='<file>') ]),
          #  Sequence([Literal('ls'), Variable(Path, placeholder='<directory>') ]),
            Sequence([Literal('abc'), Literal('efg'), Variable(Path, placeholder='<path>'), ]),
          #  Sequence([Literal('cp'), Variable(Path, placeholder='<from>'), Variable(Path, placeholder='<to>') ]),
            Sequence([Literal('cp'), Repeat(Variable(Path, placeholder='<from>')), Variable(Path, placeholder='<to>') ]),
            Sequence([Literal('git'), Repeat(
                Any([
                    #Sequence([]),
                    Literal('--version'),
                    Sequence([Literal('-c'), Variable(placeholder='<name>=<value>')]),
                    Sequence([Literal('--exec-path'), Variable(placeholder='<path>')]),
                    Literal('--help'),
                    ])
                ),
                Any([
                    Sequence([ Literal('checkout'), Variable(placeholder='<commit>') ]),
                    Sequence([ Literal('clone'), Variable(placeholder='<repository>') ]),
                    Sequence([ Literal('diff'), Variable(placeholder='<commit>') ]),
                    ]),
                ]),
          #  Sequence([Literal('echo'), Variable(placeholder='<text>'), ]),
            Sequence([Literal('echo'), Repeat(Variable(placeholder='<text>')), ]),
    ])



##A = Token.Example


class ExampleStyle(Style):
    background_color = None
    styles = {
            Token.Placeholder: "#aa8888",
            Token.Placeholder.Variable: "#aa8888",
            Token.Placeholder.Bracket: "bold #ff7777",
            Token.Placeholder.Separator: "#ee7777",
#            A.Action:  '#4444aa bg:#aaaaff',
#            A.Path:    '#0044aa',
#            A.Param:   '#ff00ff',
            Token.Aborted:    '#aaaaaa',
        }


class ExampleCommandLine(CommandLine):
    code_cls = OurGitCode
    style_cls = ExampleStyle
    prompt_cls = ShellPrompt


if __name__ == '__main__':
    cli = ExampleCommandLine()

    try:
        while True:
            shell_code = cli.read_input()
            #handlers.process(line)
            #handler.parse(
            print ('You said: %r' % shell_code.get_parse_info())
    except Exit:
        pass
