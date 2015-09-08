"""
:class:`KeyBindingManager` is a utility (or shortcut) for loading all the key
bindings in a key binding registry, with a logic set of filters to quickly to
quickly change from Vi to Emacs key bindings at runtime.

You don't have to use this, but it's practical.

Usage::

    manager = KeyBindingManager()
    cli = CommandLineInterface(key_bindings_registry=manager.registry)
"""
from __future__ import unicode_literals
from prompt_toolkit.key_binding.registry import Registry
from prompt_toolkit.key_binding.vi_state import ViState
from prompt_toolkit.key_binding.bindings.basic import load_basic_bindings, load_basic_system_bindings, load_auto_suggestion_bindings
from prompt_toolkit.key_binding.bindings.emacs import load_emacs_bindings, load_emacs_system_bindings, load_emacs_search_bindings, load_emacs_open_in_editor_bindings, load_extra_emacs_page_navigation_bindings
from prompt_toolkit.key_binding.bindings.vi import load_vi_bindings, load_vi_system_bindings, load_vi_search_bindings, load_vi_open_in_editor_bindings, load_extra_vi_page_navigation_bindings
from prompt_toolkit.filters import Never, Always, to_cli_filter

__all__ = (
    'KeyBindingManager',
)


class KeyBindingManager(object):
    """
    Utility for loading all key bindings into memory.

    :param registry: Optional `Registry` instance.
    :param enable_vi_mode: Filter to enable Vi-mode.
    :param enable_system_bindings: Filter to enable the system bindings
            (meta-! prompt and Control-Z suspension.)
    :param enable_search: Filter to enable the search bindings.
    :param enable_open_in_editor: Filter to enable open-in-editor.
    :param enable_open_in_editor: Filter to enable open-in-editor.
    :param enable_extra_page_navigation: Filter for enabling extra page navigation.
        (Bindings for up/down scrolling through long pages, like in Emacs or Vi.)
    :param enable_auto_suggestion_bindings: Filter to enable fish-style suggestions.
    :param enable_all: Filter to enable (or disable) all bindings.
    """
    def __init__(self, registry=None, enable_vi_mode=Never(), vi_state=None,
                 enable_system_bindings=Never(), enable_search=Always(),
                 enable_open_in_editor=Never(), enable_extra_page_navigation=Never(),
                 enable_auto_suggestion_bindings=Never(),
                 enable_all=Always()):

        assert registry is None or isinstance(registry, Registry)
        assert vi_state is None or isinstance(vi_state, ViState)

        # Create registry.
        self.registry = registry or Registry()

        # Vi state. (Object to keep track of in which Vi mode we are.)
        self.vi_state = vi_state or ViState()

        # Accept both Filters and booleans as input.
        enable_vi_mode = to_cli_filter(enable_vi_mode)
        enable_system_bindings = to_cli_filter(enable_system_bindings)
        enable_open_in_editor = to_cli_filter(enable_open_in_editor)
        enable_extra_page_navigation = to_cli_filter(enable_extra_page_navigation)
        enable_auto_suggestion_bindings = to_cli_filter(enable_auto_suggestion_bindings)
        enable_all = to_cli_filter(enable_all)

        # Emacs mode filter is the opposite of Vi mode.
        enable_emacs_mode = ~enable_vi_mode

        # Load basic bindings.
        load_basic_bindings(self.registry, enable_all)

        load_basic_system_bindings(self.registry,
            enable_system_bindings & enable_all)

        # Load emacs bindings.
        load_emacs_bindings(self.registry, enable_emacs_mode & enable_all)

        load_emacs_open_in_editor_bindings(
            self.registry, enable_emacs_mode & enable_open_in_editor & enable_all)

        load_emacs_search_bindings(
            self.registry, enable_emacs_mode & enable_search & enable_all)

        load_emacs_system_bindings(
            self.registry, enable_emacs_mode & enable_system_bindings & enable_all)

        load_extra_emacs_page_navigation_bindings(
            self.registry,
            enable_emacs_mode & enable_extra_page_navigation)

        # Load Vi bindings.
        load_vi_bindings(self.registry, self.vi_state, enable_visual_key=~enable_open_in_editor,
                         filter=enable_vi_mode & enable_all)

        load_vi_open_in_editor_bindings(
            self.registry, self.vi_state,
            enable_vi_mode & enable_open_in_editor & enable_all)

        load_vi_search_bindings(
            self.registry, self.vi_state,
            enable_vi_mode & enable_search & enable_all)

        load_vi_system_bindings(
            self.registry, self.vi_state,
            enable_vi_mode & enable_system_bindings & enable_all)

        load_extra_vi_page_navigation_bindings(
            self.registry,
            enable_vi_mode & enable_extra_page_navigation)

        # Suggestion bindings.
        # (This has to come at the end, because the Vi bindings also have an
        # implementation for the "right arrow", but we really want the
        # suggestion binding when a suggestion is available.)
        load_auto_suggestion_bindings(
            self.registry,
            enable_auto_suggestion_bindings)

    def reset(self):
        self.vi_state.reset()
