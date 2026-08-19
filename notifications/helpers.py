from django.core.cache import cache
from django.db.models.fields.files import FieldFile
from django.forms import model_to_dict

from notifications.registry import apply_queryset_filters, collect_invalidation_keys
from notifications.settings import get_config
from notifications.templatetags.notifications_tags import unread_count_cache_key
from notifications.utils import id2slug

# Excluded rather than allow-listed, so extra fields on a swapped-in
# model reach the json endpoints. The generic relations are rendered as
# strings below, ``data`` is attached separately, and the recipient is
# the requesting user, since the queryset starts from
# request.user.notifications.
EXCLUDED_API_FIELDS = (
    'recipient',
    'actor_content_type',
    'actor_object_id',
    'target_content_type',
    'target_object_id',
    'action_object_content_type',
    'action_object_object_id',
    'data',
)


def notification_to_dict(notification):
    """Serialize a notification's own fields for the json endpoints.

    Many to many fields are skipped: ``value_from_object`` hands back
    model instances, which JsonResponse cannot encode, and reading them
    costs a query per notification. File fields are reduced to the
    stored path for the same reason. Projects hold back their own fields
    with ``API_EXCLUDED_FIELDS``.
    """
    exclude = (
        EXCLUDED_API_FIELDS
        + tuple(get_config()['API_EXCLUDED_FIELDS'])
        + tuple(f.name for f in notification._meta.many_to_many)
    )
    struct = model_to_dict(notification, exclude=exclude)
    for key, value in struct.items():
        if isinstance(value, FieldFile):
            struct[key] = value.name
    return struct


def invalidate_unread_count_cache(user, request=None):
    """Drop the cached unread badge count(s) for ``user``.

    Without this the badge can show a stale number for up to
    ``CACHE_TIMEOUT`` seconds. Downstream packages that namespace the
    cache key (e.g. by site) register additional keys via the registry
    and they are dropped here too.
    """
    keys = [unread_count_cache_key(user, request)]
    keys.extend(collect_invalidation_keys(user, request))
    cache.delete_many(keys)


def get_object_url(instance, notification, request):
    """
    Get url representing the instance object.
    This will return instance.get_url_for_notifications()
    with parameters `notification` and `request`,
    if it is defined and get_absolute_url() otherwise
    """
    if hasattr(instance, 'get_url_for_notifications'):
        return instance.get_url_for_notifications(notification, request)
    elif hasattr(instance, 'get_absolute_url'):
        return instance.get_absolute_url()
    return None


def get_num_to_fetch(request):
    default_num_to_fetch = get_config()['NUM_TO_FETCH']
    try:
        # If they don't specify, make it 5.
        num_to_fetch = request.GET.get('max', default_num_to_fetch)
        num_to_fetch = int(num_to_fetch)
        if not (1 <= num_to_fetch <= 100):
            num_to_fetch = default_num_to_fetch
    except ValueError:  # If casting to an int fails.
        num_to_fetch = default_num_to_fetch
    return num_to_fetch


def get_notification_list(request, method_name='all'):
    num_to_fetch = get_num_to_fetch(request)
    notification_list = []
    if method_name == 'all' and get_config()['SOFT_DELETE']:
        method_name = 'active'
    mark_as_read = request.GET.get('mark_as_read')
    notification_ids = []
    qs = apply_queryset_filters(getattr(request.user.notifications, method_name)(), request)
    qs = qs.select_related('actor_content_type', 'target_content_type', 'action_object_content_type').prefetch_related(
        'actor', 'target', 'action_object'
    )
    for notification in qs[0:num_to_fetch]:
        struct = notification_to_dict(notification)
        # These keys win over anything the model declares under the same name.
        struct['slug'] = id2slug(notification.id)
        if notification.actor:
            struct['actor'] = str(notification.actor)
            actor_url = get_object_url(notification.actor, notification, request)
            if actor_url:
                struct['actor_url'] = actor_url
        if notification.target:
            struct['target'] = str(notification.target)
            target_url = get_object_url(notification.target, notification, request)
            if target_url:
                struct['target_url'] = target_url
        if notification.action_object:
            struct['action_object'] = str(notification.action_object)
            action_object_url = get_object_url(notification.action_object, notification, request)
            if action_object_url:
                struct['action_object_url'] = action_object_url
        if notification.data:
            struct['data'] = notification.data
        notification_list.append(struct)
        if mark_as_read:
            notification_ids.append(notification.id)
    if notification_ids:
        qs.filter(id__in=notification_ids).update(unread=False)
        invalidate_unread_count_cache(request.user, request)
    return notification_list
