#!/usr/bin/env python
import os
import re

from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), "README.rst")) as f:
    long_description = f.read()


def get_version(package):
    """
    Return package version as listed in `__version__` in `__init__.py`.
    """
    path = os.path.join(os.path.dirname(__file__), "src", package, "__init__.py")
    with open(path, "rb") as f:
        init_py = f.read().decode("utf-8")
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


setup(
    name="prompt_toolkit",
    author="Jonathan Slenders",
    version=get_version("prompt_toolkit"),
    url="https://github.com/prompt-toolkit/python-prompt-toolkit",
    description="Library for building powerful interactive command lines in Python",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={"prompt_toolkit": ["py.typed"]},
    install_requires=["wcwidth"],
    # We require Python 3.6.2 for three reasons:
    # - Syntax for variable annotations - PEP 526.
    # - Asynchronous generators - PEP 525.
    # - New type annotations in 3.6.2 (i.e. NoReturn)
    # Also, 3.6.0 doesn't have `typing.AsyncGenerator` yet. 3.6.1 does.
    # Python 3.7 is suggested, because:
    # - Context variables - PEP 567
    # (The current application is derived from a context variable.)
    # There is no intension to support Python 3.5, because prompt_toolkit 2.0
    # does run fine on any older Python version starting from Python 2.6, and
    # it is possible to write code that runs both against prompt_toolkit
    # version 2 and 3.
    python_requires=">=3.6.2",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python",
        "Topic :: Software Development",
    ],
)
