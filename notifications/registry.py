"""Extension hooks for downstream packages.

Downstream packages (e.g. django-notifications-community-sites) plug into
the queryset and cache-key flow without forking views, helpers, or
template tags. With nothing registered each hook is a no-op, so the
default behaviour of this package is unchanged.

Register from your AppConfig.ready()::

    from notifications.registry import register_queryset_filter

    def my_filter(queryset, request):
        return queryset.filter(...)

    register_queryset_filter(my_filter)
"""

_queryset_filters = []
_cache_key_modifiers = []
_cache_invalidation_keys = []


def register_queryset_filter(fn):
    """Register a callable applied wherever the package builds a Notification queryset.

    ``fn`` receives ``(queryset, request)`` and must return a queryset.
    Callbacks stack in registration order. ``request`` may be ``None``
    when called from a context with no request available (e.g. the
    ``has_notification`` filter).
    """
    _queryset_filters.append(fn)


def apply_queryset_filters(queryset, request):
    """Run ``queryset`` through the registered filters in order."""
    for fn in _queryset_filters:
        queryset = fn(queryset, request)
    return queryset


def register_cache_key_modifier(fn):
    """Register a callable that derives the unread-count cache key.

    ``fn`` receives ``(base_key, user, request)`` and must return a
    string. Callbacks stack: each receives the previous return value as
    ``base_key``. ``request`` may be ``None``.
    """
    _cache_key_modifiers.append(fn)


def derive_cache_key(base_key, user, request=None):
    """Run ``base_key`` through the registered modifiers in order."""
    for fn in _cache_key_modifiers:
        base_key = fn(base_key, user, request)
    return base_key


def register_cache_invalidation_keys(fn):
    """Register a callable that returns extra cache keys to drop on mutation.

    ``fn`` receives ``(user, request)`` and must return an iterable of
    strings. ``invalidate_unread_count_cache`` collects these alongside
    the base key, so downstream packages with multiple cache-key
    variants per user (e.g. one per site) can invalidate all of them.
    """
    _cache_invalidation_keys.append(fn)


def collect_invalidation_keys(user, request=None):
    """Collect every extra cache key registered for ``user``."""
    keys = []
    for fn in _cache_invalidation_keys:
        keys.extend(fn(user, request))
    return keys
