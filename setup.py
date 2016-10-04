#!/usr/bin/env python
import os
import sys
from setuptools import setup, find_packages

_here = os.path.dirname(__file__)
with open(os.path.join(_here, 'README.rst')) as f:
    long_description = f.read()


def get_version(package):
    """
    Return package version as listed in `__version__` in `__init__.py`.
    """
    path = os.path.join(_here, package, '__init__.py')
    with open(path) as fp:
        for line in fp:
            if line.startswith('__version__'):
                _locals = {}
                exec (line, None, _locals)
                return _locals['__version__']

needs_pytest = set(['pytest', 'test', 'ptr']).intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(
    name='prompt_toolkit',
    author='Jonathan Slenders',
    version=get_version('prompt_toolkit'),
    url='https://github.com/jonathanslenders/python-prompt-toolkit',
    description=
        'Library for building powerful interactive command lines in Python',
    long_description=long_description,
    packages=find_packages('.'),
    install_requires=[
        'six>=1.9.0',
        'wcwidth',
    ],
    extras_require={
        'clipboard': 'pyperclip',
        'highlight': 'pygments',
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python',
        'Topic :: Software Development',
    ],
    setup_requires=pytest_runner,
    tests_require=[
        'pytest',
        'pytest-cov',
        'prompt_toolkit[clipboard]',
        'prompt_toolkit[highlight]',
    ],
    test_suite='tests',
)
