"""
Key bindings registry.

A `KeyBindings` object is a container that holds a list of key bindings. It has a
very efficient internal data structure for checking which key bindings apply
for a pressed key.

Typical usage::

    r = KeyBindings()

    @r.add(Keys.ControlX, Keys.ControlC, filter=INSERT)
    def handler(event):
        # Handle ControlX-ControlC key sequence.
        pass

It is also possible to combine multiple KeyBindings objects. We do this in the
default key bindings. There are some KeyBindings objects that contain the Emacs
bindings, while others contain the Vi bindings. They are merged together using
a `MergedKeyBindings`.

We also have a `ConditionalKeyBindings` object that can enable/disable a group of
key bindings at once.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod, abstractproperty

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.filters import AppFilter, to_app_filter, Never
from prompt_toolkit.keys import Key, Keys

from six import text_type, with_metaclass

__all__ = (
    'KeyBindingsBase',
    'KeyBindings',
    'ConditionalKeyBindings',
    'MergedKeyBindings',
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


class KeyBindingsBase(with_metaclass(ABCMeta, object)):
    """
    Interface for a KeyBindings.
    """
    @abstractproperty
    def _version(self):
        """
        For cache invalidation. - This should increase every time that
        something changes.
        """
        return 0

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

    # `add` and `remove` don't have to be part of this interface.


class KeyBindings(KeyBindingsBase):
    """
    Key binding.
    """
    def __init__(self):
        self.bindings = []
        self._get_bindings_for_keys_cache = SimpleCache(maxsize=10000)
        self._get_bindings_starting_with_keys_cache = SimpleCache(maxsize=1000)
        self.__version = 0  # For cache invalidation.

    def _clear_cache(self):
        self.__version += 1
        self._get_bindings_for_keys_cache.clear()
        self._get_bindings_starting_with_keys_cache.clear()

    @property
    def _version(self):
        return self.__version

    def add(self, *keys, **kwargs):
        """
        Decorator for adding a key bindings.

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

        assert not kwargs
        assert keys
        assert all(isinstance(k, (Key, text_type)) for k in keys), \
            'Key bindings should consist of Key and string (unicode) instances.'
        assert callable(save_before)

        if isinstance(filter, Never):
            # When a filter is Never, it will always stay disabled, so in that
            # case don't bother putting it in the key bindings. It will slow
            # down every key press otherwise.
            def decorator(func):
                return func
        else:
            def decorator(func):
                self.bindings.append(
                    _Binding(keys, func, filter=filter, eager=eager,
                             save_before=save_before))
                self._clear_cache()

                return func
        return decorator

    def remove_binding(self, function):
        """
        Remove a key binding.

        This expects a function that was given to `add` method as
        parameter. Raises `ValueError` when the given function was not
        registered before.
        """
        assert callable(function)

        for b in self.bindings:
            if b.handler == function:
                self.bindings.remove(b)
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
            for b in self.bindings:
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
            for b in self.bindings:
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


class _Proxy(KeyBindingsBase):
    """
    Common part for ConditionalKeyBindings and MergedKeyBindings.
    """
    def __init__(self):
        # `KeyBindings` to be synchronized with all the others.
        self._bindings2 = KeyBindings()
        self._last_version = None

    def _update_cache(self):
        """
        If `self._last_version` is outdated, then this should update
        the version and `self._bindings2`.
        """
        raise NotImplementedError

    # Proxy methods to self._bindings2.

    @property
    def bindings(self):
        self._update_cache()
        return self._bindings2.bindings

    @property
    def _version(self):
        self._update_cache()
        return self._last_version

    def get_bindings_for_keys(self, *a, **kw):
        self._update_cache()
        return self._bindings2.get_bindings_for_keys(*a, **kw)

    def get_bindings_starting_with_keys(self, *a, **kw):
        self._update_cache()
        return self._bindings2.get_bindings_starting_with_keys(*a, **kw)


class ConditionalKeyBindings(_Proxy):
    """
    Wraps around a `KeyBindings`. Disable/enable all the key bindings according to
    the given (additional) filter.::

        @Condition
        def setting_is_true(app):
            return True  # or False

        registy = ConditionalKeyBindings(registry, setting_is_true)

    When new key bindings are added to this object. They are also
    enable/disabled according to the given `filter`.

    :param registries: List of `KeyBindings` objects.
    :param filter: `AppFilter` object.
    """
    def __init__(self, key_bindings, filter=True):
        assert isinstance(key_bindings, KeyBindingsBase)
        _Proxy.__init__(self)

        self.key_bindings = key_bindings
        self.filter = to_app_filter(filter)

    def _update_cache(self):
        " If the original key bindings was changed. Update our copy version. "
        expected_version = self.key_bindings._version

        if self._last_version != expected_version:
            bindings2 = KeyBindings()

            # Copy all bindings from `self.key_bindings`, adding our condition.
            for b in self.key_bindings.bindings:
                bindings2.bindings.append(
                    _Binding(
                        keys=b.keys,
                        handler=b.handler,
                        filter=self.filter & b.filter,
                        eager=b.eager,
                        save_before=b.save_before))

            self._bindings2 = bindings2
            self._last_version = expected_version


class MergedKeyBindings(_Proxy):
    """
    Merge multiple registries of key bindings into one.

    This class acts as a proxy to multiple `KeyBindings` objects, but behaves as
    if this is just one bigger `KeyBindings`.

    :param registries: List of `KeyBindings` objects.
    """
    def __init__(self, registries):
        assert all(isinstance(r, KeyBindingsBase) for r in registries)
        _Proxy.__init__(self)
        self.registries = registries

    def _update_cache(self):
        """
        If one of the original registries was changed. Update our merged
        version.
        """
        expected_version = tuple(r._version for r in self.registries)

        if self._last_version != expected_version:
            bindings2 = KeyBindings()

            for reg in self.registries:
                bindings2.bindings.extend(reg.bindings)

            self._bindings2 = bindings2
            self._last_version = expected_version


class DynamicRegistry(_Proxy):
    """
    KeyBindings class that can dynamically returns any KeyBindings.

    :param get_key_bindings: Callable that returns a :class:`.KeyBindings` instance.
    """
    def __init__(self, get_key_bindings):
        assert callable(get_key_bindings)
        self.get_key_bindings = get_key_bindings
        self.__version = 0
        self._last_child_version = None
        self._dummy = KeyBindings()  # Empty key bindings.

    def _update_cache(self):
        key_bindings = self.get_key_bindings() or self._dummy
        assert isinstance(key_bindings, KeyBindingsBase)
        version = id(key_bindings), key_bindings._version

        self._bindings2 = key_bindings
        self._last_version = version
