#!/usr/bin/env python
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
        name='pyline',
        author='Jonathan Slenders',
        version='0.1',
        license='LICENSE.txt',
        url='https://github.com/jonathanslenders/pyline',

        description='',
        long_description='',
        packages=['pyline'],
        install_requires = [ 'pygments', 'docopt', 'six' ],
        #install_requires = [ 'pygments', 'docopt', 'wcwidth', ], # TODO: add wcwidth when released on pypi
        scripts = [
            'bin/pyline-python-repl',
        ]
)
