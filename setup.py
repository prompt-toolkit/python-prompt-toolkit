#!/usr/bin/env python
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
        name='prompt_toolkit',
        author='Jonathan Slenders',
        version='0.1',
        license='LICENSE.txt',
        url='https://github.com/jonathanslenders/python-prompt-toolkit',

        description='',
        long_description='',
        packages=['prompt_toolkit'],
        install_requires = [ 'pygments', 'docopt', 'six' ],
        #install_requires = [ 'pygments', 'docopt', 'wcwidth', ], # TODO: add wcwidth when released on pypi
        scripts = [
            'bin/prompt-toolkit-python-repl',
        ]
)
