"""
Key bindings registry.

A `Registry` object is a container that holds a list of key bindings. It has a
very efficient internal data structure for checking which key bindings apply
for a pressed key.

Typical usage::

    r = Registry()

    @r.add_binding(Keys.ControlX, Keys.ControlC, filter=INSERT)
    def handler(event):
        # Handle ControlX-ControlC key sequence.
        pass


It is also possible to combine multiple registries. We do this in the default
key bindings. There are some registries that contain Emacs bindings, while
others contain the Vi bindings. They are merged together using a
`MergedRegistry`.

We also have a `ConditionalRegistry` object that can enable/disable a group of
key bindings at once.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.filters import AppFilter, to_app_filter, Never
from prompt_toolkit.keys import Key, Keys

from six import text_type, with_metaclass

__all__ = (
    'BaseRegistry',
    'Registry',
    'ConditionalRegistry',
    'MergedRegistry',
    'DynamicRegistry',
)


class _Binding(object):
    """
    (Immutable binding class.)
    """
    def __init__(self, keys, handler, filter=None, eager=None, save_before=None):
        assert isinstance(keys, tuple)
        assert callable(handler)
        assert isinstance(filter, AppFilter)
        assert isinstance(eager, AppFilter)
        assert callable(save_before)

        self.keys = keys
        self.handler = handler
        self.filter = filter
        self.eager = eager
        self.save_before = save_before

    def call(self, event):
        return self.handler(event)

    def __repr__(self):
        return '%s(keys=%r, handler=%r)' % (
            self.__class__.__name__, self.keys, self.handler)


class BaseRegistry(with_metaclass(ABCMeta, object)):
    """
    Interface for a Registry.
    """
    _version = 0  # For cache invalidation.

    @abstractmethod
    def get_bindings_for_keys(self, keys):
        """
        Return a list of key bindings that can handle these keys.
        (This return also inactive bindings, so the `filter` still has to be
        called, for checking it.)

        :param keys: tuple of keys.
        """
        return []

    @abstractmethod
    def get_bindings_starting_with_keys(self, keys):
        """
        Return a list of key bindings that handle a key sequence starting with
        `keys`. (It does only return bindings for which the sequences are
        longer than `keys`. And like `get_bindings_for_keys`, it also includes
        inactive bindings.)

        :param keys: tuple of keys.
        """
        return []

    # `add_binding` and `remove_binding` don't have to be part of this
    # interface.


class Registry(BaseRegistry):
    """
    Key binding registry.
    """
    def __init__(self):
        self.key_bindings = []
        self._get_bindings_for_keys_cache = SimpleCache(maxsize=10000)
        self._get_bindings_starting_with_keys_cache = SimpleCache(maxsize=1000)
        self._version = 0  # For cache invalidation.

    def _clear_cache(self):
        self._version += 1
        self._get_bindings_for_keys_cache.clear()
        self._get_bindings_starting_with_keys_cache.clear()

    def add_binding(self, *keys, **kwargs):
        """
        Decorator for annotating key bindings.

        :param filter: :class:`~prompt_toolkit.filters.AppFilter` to determine
            when this key binding is active.
        :param eager: :class:`~prompt_toolkit.filters.AppFilter` or `bool`.
            When True, ignore potential longer matches when this key binding is
            hit. E.g. when there is an active eager key binding for Ctrl-X,
            execute the handler immediately and ignore the key binding for
            Ctrl-X Ctrl-E of which it is a prefix.
        :param save_before: Callable that takes an `Event` and returns True if
            we should save the current buffer, before handling the event.
            (That's the default.)
        """
        filter = to_app_filter(kwargs.pop('filter', True))
        eager = to_app_filter(kwargs.pop('eager', False))
        save_before = kwargs.pop('save_before', lambda e: True)
        to_app_filter(kwargs.pop('invalidate_ui', True))  # Deprecated! (ignored.)

        assert not kwargs
        assert keys
        assert all(isinstance(k, (Key, text_type)) for k in keys), \
            'Key bindings should consist of Key and string (unicode) instances.'
        assert callable(save_before)

        if isinstance(filter, Never):
            # When a filter is Never, it will always stay disabled, so in that case
            # don't bother putting it in the registry. It will slow down every key
            # press otherwise.
            def decorator(func):
                return func
        else:
            def decorator(func):
                self.key_bindings.append(
                    _Binding(keys, func, filter=filter, eager=eager,
                             save_before=save_before))
                self._clear_cache()

                return func
        return decorator

    def remove_binding(self, function):
        """
        Remove a key binding.

        This expects a function that was given to `add_binding` method as
        parameter. Raises `ValueError` when the given function was not
        registered before.
        """
        assert callable(function)

        for b in self.key_bindings:
            if b.handler == function:
                self.key_bindings.remove(b)
                self._clear_cache()
                return

        # No key binding found for this function. Raise ValueError.
        raise ValueError('Binding not found: %r' % (function, ))

    def get_bindings_for_keys(self, keys):
        """
        Return a list of key bindings that can handle this key.
        (This return also inactive bindings, so the `filter` still has to be
        called, for checking it.)

        :param keys: tuple of keys.
        """
        def get():
            result = []
            for b in self.key_bindings:
                if len(keys) == len(b.keys):
                    match = True
                    any_count = 0

                    for i, j in zip(b.keys, keys):
                        if i != j and i != Keys.Any:
                            match = False
                            break

                        if i == Keys.Any:
                            any_count += 1

                    if match:
                        result.append((any_count, b))

            # Place bindings that have more 'Any' occurences in them at the end.
            result = sorted(result, key=lambda item: -item[0])

            return [item[1] for item in result]

        return self._get_bindings_for_keys_cache.get(keys, get)

    def get_bindings_starting_with_keys(self, keys):
        """
        Return a list of key bindings that handle a key sequence starting with
        `keys`. (It does only return bindings for which the sequences are
        longer than `keys`. And like `get_bindings_for_keys`, it also includes
        inactive bindings.)

        :param keys: tuple of keys.
        """
        def get():
            result = []
            for b in self.key_bindings:
                if len(keys) < len(b.keys):
                    match = True
                    for i, j in zip(b.keys, keys):
                        if i != j and i != Keys.Any:
                            match = False
                            break
                    if match:
                        result.append(b)
            return result

        return self._get_bindings_starting_with_keys_cache.get(keys, get)


class _ProxyMixin(BaseRegistry):
    """
    Common part for ConditionalRegistry and MergedRegistry.
    """
    def __init__(self):
        # `Registry` to be synchronized with all the others.
        self._registry2 = Registry()
        self._last_version = None

    def _update_cache(self):
        raise NotImplementedError

    # Proxy methods to self._registry2.

    @property
    def key_bindings(self):
        self._update_cache()
        return self._registry2.key_bindings

    @property
    def _version(self):
        self._update_cache()
        return self._last_version

    def get_bindings_for_keys(self, *a, **kw):
        self._update_cache()
        return self._registry2.get_bindings_for_keys(*a, **kw)

    def get_bindings_starting_with_keys(self, *a, **kw):
        self._update_cache()
        return self._registry2.get_bindings_starting_with_keys(*a, **kw)


class ConditionalRegistry(_ProxyMixin):
    """
    Wraps around a `Registry`. Disable/enable all the key bindings according to
    the given (additional) filter.::

        @Condition
        def setting_is_true(app):
            return True  # or False

        registy = ConditionalRegistry(registry, setting_is_true)

    When new key bindings are added to this object. They are also
    enable/disabled according to the given `filter`.

    :param registries: List of `Registry` objects.
    :param filter: `AppFilter` object.
    """
    def __init__(self, registry, filter=True):
        assert isinstance(registry, BaseRegistry)
        _ProxyMixin.__init__(self)

        self.registry = registry
        self.filter = to_app_filter(filter)

    def _update_cache(self):
        " If the original registry was changed. Update our copy version. "
        expected_version = self.registry._version

        if self._last_version != expected_version:
            registry2 = Registry()

            # Copy all bindings from `self.registry`, adding our condition.
            for b in self.registry.key_bindings:
                registry2.key_bindings.append(
                    _Binding(
                        keys=b.keys,
                        handler=b.handler,
                        filter=self.filter & b.filter,
                        eager=b.eager,
                        save_before=b.save_before))

            self._registry2 = registry2
            self._last_version = expected_version


class MergedRegistry(_ProxyMixin):
    """
    Merge multiple registries of key bindings into one.

    This class acts as a proxy to multiple `Registry` objects, but behaves as
    if this is just one bigger `Registry`.

    :param registries: List of `Registry` objects.
    """
    def __init__(self, registries):
        assert all(isinstance(r, BaseRegistry) for r in registries)
        _ProxyMixin.__init__(self)
        self.registries = registries

    def _update_cache(self):
        """
        If one of the original registries was changed. Update our merged
        version.
        """
        expected_version = tuple(r._version for r in self.registries)

        if self._last_version != expected_version:
            registry2 = Registry()

            for reg in self.registries:
                registry2.key_bindings.extend(reg.key_bindings)

            self._registry2 = registry2
            self._last_version = expected_version


class DynamicRegistry(_ProxyMixin):
    """
    Registry class that can dynamically returns any Registry.

    :param get_registry: Callable that returns a :class:`.Registry` instance.
    """
    def __init__(self, get_registry):
        assert callable(get_registry)
        self.get_registry = get_registry
        self.__version = 0
        self._last_child_version = None
        self._dummy = Registry()  # Empty registry.

    def _update_cache(self):
        registry = self.get_registry() or self._dummy
        assert isinstance(registry, BaseRegistry)
        version = id(registry), registry._version

        self._registry2 = registry
        self._last_version = version
