"""
Styling for prompt_toolkit applications.
"""
from __future__ import unicode_literals

from .base import *
from .defaults import *
from .from_dict import *
from .from_pygments import *
from .utils import *


#: The default built-in style.
#: (For backwards compatibility, when Pygments is installed, this includes the
#: default Pygments style.)
try:
    # must come before pygments imports
    from ..lazyasd import load_module_in_background
    load_module_in_background('pkg_resources', debug='PROMPT_TOOLKIT_DEBUG',
        replacements={'pygments.plugin': 'pkg_resources'})
    import pygments
except ImportError:
    DEFAULT_STYLE = style_from_dict(DEFAULT_STYLE_EXTENSIONS)
else:
    DEFAULT_STYLE = style_from_pygments()
