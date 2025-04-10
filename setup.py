#!/usr/bin/env python
import os

from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), "README.rst")) as f:
    long_description = f.read()


setup(
    name="prompt_toolkit",
    author="Jonathan Slenders",
    version="3.0.50",
    url="https://github.com/prompt-toolkit/python-prompt-toolkit",
    description="Library for building powerful interactive command lines in Python",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={"prompt_toolkit": ["py.typed"]},
    install_requires=["wcwidth"],
    python_requires=">=3.8.0",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python",
        "Topic :: Software Development",
    ],
)
