"""Django notifications template tags file"""

import json
import re

from django.core.cache import cache
from django.template import Library
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from notifications import settings

register = Library()


def unread_count_cache_key(user):
    return f'notifications_unread_count_{user.pk}'


def get_cached_notification_unread_count(user):
    return cache.get_or_set(
        unread_count_cache_key(user),
        user.notifications.unread().count,
        settings.get_config()['CACHE_TIMEOUT'],
    )


@register.simple_tag(takes_context=True)
def notifications_unread(context):
    user = user_context(context)
    if not user:
        return ''
    return get_cached_notification_unread_count(user)


@register.filter
def has_notification(user):
    if user:
        return user.notifications.unread().exists()
    return False


_JS_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_$][a-zA-Z0-9_$]*(\.[a-zA-Z_$][a-zA-Z0-9_$]*)*$')
_JSON_SCRIPT_ESCAPES = {ord('>'): '\\u003E', ord('<'): '\\u003C', ord('&'): '\\u0026'}


@register.simple_tag
def register_notify_callbacks(
    badge_class='live_notify_badge',
    menu_class='live_notify_list',
    refresh_period=15,
    callbacks='',
    api_name='list',
    fetch=5,
    nonce=None,
    mark_as_read=False,
):
    refresh_period = int(refresh_period) * 1000

    if api_name == 'list':
        api_url = reverse('notifications:live_unread_notification_list')
    elif api_name == 'count':
        api_url = reverse('notifications:live_unread_notification_count')
    else:
        return ''

    callback_list = []
    if callbacks:
        for cb in callbacks.split(','):
            cb = cb.strip()
            if cb:
                if not _JS_IDENTIFIER_RE.match(cb):
                    raise ValueError(f'Invalid callback name: {cb!r}. Must be a valid JavaScript identifier.')
                callback_list.append(cb)

    config = {
        'badgeClass': str(badge_class),
        'menuClass': str(menu_class),
        'apiUrl': api_url,
        'fetchCount': int(fetch),
        'unreadUrl': reverse('notifications:unread'),
        'markAllUnreadUrl': reverse('notifications:mark_all_as_read'),
        'refreshPeriod': refresh_period,
        'markAsRead': str(mark_as_read).lower() == 'true',
        'callbacks': callback_list,
    }

    # mark_safe is safe here: json.dumps produces valid JSON, and
    # _JSON_SCRIPT_ESCAPES neutralizes </script> injection. The tag
    # type="application/json" is non-executable by the browser.
    config_json = json.dumps(config, separators=(',', ':'))
    config_json = config_json.translate(_JSON_SCRIPT_ESCAPES)

    if nonce:
        return format_html(
            '<script type="application/json" id="notify-config" nonce="{}">{}</script>',
            nonce,
            mark_safe(config_json),
        )
    return format_html(
        '<script type="application/json" id="notify-config">{}</script>',
        mark_safe(config_json),
    )


@register.simple_tag(takes_context=True)
def live_notify_badge(context, badge_class='live_notify_badge'):
    user = user_context(context)
    if not user:
        return ''

    return format_html(
        "<span class='{}'>{}</span>",
        badge_class,
        get_cached_notification_unread_count(user),
    )


@register.simple_tag
def live_notify_list(list_class='live_notify_list'):
    return format_html("<ul class='{}'></ul>", list_class)


def user_context(context):
    if 'user' not in context:
        return None

    request = context['request']
    user = request.user
    user_is_anonymous = user.is_anonymous

    if user_is_anonymous:
        return None
    return user
