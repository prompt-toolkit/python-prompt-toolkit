#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
        name='prompt_toolkit',
        author='Jonathan Slenders',
        version='0.3',
        license='LICENSE.txt',
        url='https://github.com/jonathanslenders/python-prompt-toolkit',

        description='',
        long_description='',
        packages=find_packages('.'),
        install_requires = [ 'pygments', 'docopt', 'six' ],
        #install_requires = [  'wcwidth', ], # TODO: add wcwidth when released on pypi
        extra_requires=[
            # Required for the Python repl
            'jedi'
        ],
        scripts = [
            'bin/ptpython',
        ]
)
