#!/bin/bash

mypy prompt_toolkit | grep -v "Name '_' already defined" | (! grep ': error:')
