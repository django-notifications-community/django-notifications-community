# django-notifications (community fork)

[![tests](https://github.com/django-notifications-community/django-notifications-community/actions/workflows/test.yml/badge.svg)](https://github.com/django-notifications-community/django-notifications-community/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/django-notifications-community.svg)](https://pypi.org/project/django-notifications-community/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-notifications-community.svg)](https://pypi.org/project/django-notifications-community/)
[![Django versions](https://img.shields.io/pypi/djversions/django-notifications-community.svg?label=django)](https://pypi.org/project/django-notifications-community/)

> **This is a community-maintained fork of
> [django-notifications/django-notifications](https://github.com/django-notifications/django-notifications).**
>
> The original project appears unmaintained: version 1.9.0 (with Django 5.x and
> Python 3.13 support) has been sitting unreleased on `master`, and requests for
> PyPI and maintainer access have gone unanswered. See the discussion in
> [upstream issue #416](https://github.com/django-notifications/django-notifications/issues/416)
> for context.
>
> All credit for the original work goes to Justin Quick, Yang Yubo, and the
> `django-notifications` team (see [`AUTHORS.txt`](AUTHORS.txt)). This fork
> exists solely to continue shipping releases to PyPI and keep the project
> compatible with current Django and Python versions. If upstream resumes
> active maintenance, we will happily coordinate and, where appropriate,
> redirect users back.
>
> **Drop-in replacement.** The Python import path is unchanged
> (`import notifications`). To switch from the original package:
>
> ```bash
> pip uninstall django-notifications-hq
> pip install django-notifications-community
> ```
>
> or with [uv](https://docs.astral.sh/uv/):
>
> ```bash
> uv remove django-notifications-hq
> uv add django-notifications-community
> ```
>
> Editing `pyproject.toml` by hand and running `uv sync` can leave the
> shared `notifications/` import path in a half-installed state, since
> both distributions write to the same directory. Use `uv remove` +
> `uv add` (or `uv pip install --reinstall django-notifications-community`
> as a fallback) to avoid it.

## Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Settings](#settings)
- [Multi-site](#multi-site)
- [Generating notifications](#generating-notifications)
- [QuerySet and model methods](#queryset-and-model-methods)
- [Template tags](#template-tags)
- [Live-updater API](#live-updater-api)
- [Serializing the notification model](#serializing-the-notification-model)
- [AbstractNotification model](#abstractnotification-model)
- [Notes](#notes)
- [Credits](#credits)
- [Contributing](#contributing)

## Overview

[django-notifications](https://github.com/django-notifications/django-notifications)
is a GitHub-style notifications app for Django, derived from
[django-activity-stream](https://github.com/justquick/django-activity-stream).

The major difference between `django-notifications` and
`django-activity-stream`:

- `django-notifications` is for building something like GitHub "Notifications".
- `django-activity-stream` is for building a GitHub "News Feed".

A notification is an action event, categorized by four components:

- `Actor` — the object that performed the activity.
- `Verb` — the verb phrase that identifies the action.
- `Action Object` — *(optional)* the object linked to the action itself.
- `Target` — *(optional)* the object the activity was performed on.

`Actor`, `Action Object`, and `Target` are `GenericForeignKey`s to any
arbitrary Django object. An action describes something that was performed
(`Verb`) at some instant in time by an `Actor` on an optional `Target`,
resulting in an `Action Object` being created, updated, or deleted.

For example: [justquick](https://github.com/justquick/) `(actor)` *closed*
`(verb)` [issue 2](https://github.com/justquick/django-activity-stream/issues/2)
`(action_object)` on
[activity-stream](https://github.com/justquick/django-activity-stream/)
`(target)` 12 hours ago.

Nomenclature is based on the Activity Streams spec:
<https://activitystrea.ms/specs/atom/1.0/>.

## Requirements

- Python 3.10, 3.11, 3.12, 3.13
- Django 5.2, 6.0 (Django 6.0 requires Python 3.12+)

If you need Django 4.2 or 5.1, pin
`django-notifications-community<1.12`.

If you need Python 3.9, pin
`django-notifications-community<1.10`.

## Installation

Install with pip:

```bash
pip install django-notifications-community
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv add django-notifications-community
```

Add `notifications` to `INSTALLED_APPS`. It should come after any apps that
generate notifications (like `django.contrib.auth`):

```python
INSTALLED_APPS = [
    'django.contrib.auth',
    ...
    'notifications',
    ...
]
```

Include the notifications URLs in your urlconf:

```python
urlpatterns = [
    ...
    path('inbox/notifications/', include('notifications.urls', namespace='notifications')),
    ...
]
```

Run the migrations:

```bash
python manage.py migrate notifications
```

## Settings

All configuration lives in a single `DJANGO_NOTIFICATIONS_CONFIG` dict in
`settings.py`. Defaults:

```python
DJANGO_NOTIFICATIONS_CONFIG = {
    'PAGINATE_BY': 20,
    'USE_JSONFIELD': False,
    'SOFT_DELETE': False,
    'NUM_TO_FETCH': 10,
    'CACHE_TIMEOUT': 2,
}
```

| Key             | Default | Purpose                                                                                           |
|-----------------|---------|---------------------------------------------------------------------------------------------------|
| `PAGINATE_BY`   | `20`    | Page size for the list views.                                                                     |
| `USE_JSONFIELD` | `False` | Persist extra kwargs passed to `notify.send()` on `Notification.data`.                            |
| `SOFT_DELETE`   | `False` | Flip the delete view from row removal to setting `deleted=True`. See [Soft delete](#soft-delete). |
| `NUM_TO_FETCH`  | `10`    | Default page size for the live-updater JSON endpoints.                                            |
| `CACHE_TIMEOUT` | `2`     | Seconds to cache `user.notifications.unread().count`. `0` disables caching.                       |

### Extra data

With `USE_JSONFIELD` on, any extra keyword arguments passed to
`notify.send(...)` are stored on the notification's `.data` attribute, JSON
serialized. Pass only JSON-serializable values.

### Soft delete

With `SOFT_DELETE` on, `delete/<int:slug>/` flips `Notification.deleted` to
`True` instead of removing the row. The `unread` and `read` querysets gain a
`deleted=False` filter, and the `deleted`, `active`, `mark_all_as_deleted`,
and `mark_all_as_active` queryset methods become usable. See
[QuerySet methods](#queryset-methods) below.

## Multi-site

If you serve more than one site from the same Django project (different
domains or `SITE_ID`s), install the companion package
[`django-notifications-community-sites`](https://github.com/django-notifications-community/django-notifications-community-sites)
to scope notifications to the current site. The cleanest way is via the
`sites` extra:

```bash
pip install "django-notifications-community[sites]"
```

That pulls the companion in automatically. See its README for the rest
of the setup (an extra app in `INSTALLED_APPS`, the
`NOTIFICATIONS_NOTIFICATION_MODEL` setting, and `SITE_ID`).

The companion plugs into the extension hooks added in 1.12.0
(`notifications.registry`), so views, helpers, and template tags pick up
site scoping without any change to your code or templates here.

## Generating notifications

The typical pattern is to send a notification from a signal handler on one
of your own models:

```python
from django.db.models.signals import post_save
from notifications.signals import notify
from myapp.models import MyModel

def my_handler(sender, instance, created, **kwargs):
    notify.send(instance, verb='was saved')

post_save.connect(my_handler, sender=MyModel)
```

You can also call `notify.send()` directly anywhere in your code:

```python
from notifications.signals import notify

notify.send(user, recipient=user, verb='you reached level 10')
```

> **Note:** `notify.send()` uses `bulk_create` internally, so `post_save`
> handlers registered on the `Notification` model itself will not fire. See
> [Bulk creation and signals](#bulk-creation-and-signals).

Full signature:

```python
notify.send(
    actor, recipient, verb,
    action_object, target,
    level, description, public, timestamp,
    **kwargs,
)
```

Arguments:

- **actor** *(required)* — any object. Use `sender` instead of `actor` if
  you're passing keyword arguments.
- **recipient** *(required)* — a single `User`, a `Group`, a `User`
  queryset, or a list of `User`s.
- **verb** *(required)* — a string.
- **action_object** — any object.
- **target** — any object.
- **level** — one of `Notification.LEVELS` (`'success'`, `'info'`,
  `'warning'`, `'error'`). Defaults to `'info'`.
- **description** — a string.
- **public** — a bool. Defaults to `True`.
- **timestamp** — a `datetime`. Defaults to `timezone.now()`.

## QuerySet and model methods

### QuerySet methods

The `Notification` manager is built from a custom `QuerySet` via Django's
`QuerySet.as_manager()`, so queryset methods are available on the manager,
on related managers, and on any further-filtered queryset:

```python
Notification.objects.unread()

user = User.objects.get(pk=pk)
user.notifications.unread()
```

Available methods:

| Method                                | Purpose                                                          |
|---------------------------------------|------------------------------------------------------------------|
| `qs.unread()`                         | Unread notifications. With `SOFT_DELETE=True`, excludes deleted. |
| `qs.read()`                           | Read notifications. With `SOFT_DELETE=True`, excludes deleted.   |
| `qs.unsent()`                         | `emailed=False`.                                                 |
| `qs.sent()`                           | `emailed=True`.                                                  |
| `qs.mark_all_as_read([recipient])`    | Mark all unread rows as read.                                    |
| `qs.mark_all_as_unread([recipient])`  | Mark all read rows as unread.                                    |
| `qs.mark_as_sent([recipient])`        | Mark unsent rows as sent.                                        |
| `qs.mark_as_unsent([recipient])`      | Mark sent rows as unsent.                                        |
| `qs.deleted()`                        | Rows with `deleted=True`. Requires `SOFT_DELETE=True`.           |
| `qs.active()`                         | Rows with `deleted=False`. Requires `SOFT_DELETE=True`.          |
| `qs.mark_all_as_deleted([recipient])` | Flip to `deleted=True`. Requires `SOFT_DELETE=True`.             |
| `qs.mark_all_as_active([recipient])`  | Flip to `deleted=False`. Requires `SOFT_DELETE=True`.            |

### Model methods

- `obj.timesince([datetime])` — wrapper around Django's `timesince`.
- `obj.naturalday()` / `obj.naturaltime()` — wrappers around the
  `django.contrib.humanize` helpers of the same name.
- `obj.mark_as_read()` / `obj.mark_as_unread()` — flip `unread` on a
  single row.
- `obj.slug` — URL-safe encoded id, used by the `mark-as-read`,
  `mark-as-unread`, and `delete` views.

## Template tags

Load the tag library in your template:

```django
{% load notifications_tags %}
```

### `notifications_unread`

```django
{% notifications_unread %}
```

Returns the unread count for the current user, or an empty string for
anonymous users. Storing it in a variable is usually what you want:

```django
{% notifications_unread as unread_count %}
{% if unread_count %}
    You have <strong>{{ unread_count }}</strong> unread notifications.
{% endif %}
```

## Live-updater API

A small JavaScript API periodically polls the server to keep unread counts
and lists up to date. Two endpoints are provided for unread data:

1. `api/unread_count/` — `{"unread_count": 1}`
2. `api/unread_list/` — `{"unread_count": 1, "unread_list": [ ... ]}`

Matching `api/all_count/` and `api/all_list/` endpoints cover *all*
notifications (read and unread) and follow the same key pattern —
`{scope}_count` and `{scope}_list`, where `scope` mirrors the endpoint
segment (so `all_count`, `all_list`).

Notification JSON is produced via Django's `model_to_dict`. Each list entry
also exposes `target_url`, `actor_url`, and `action_object_url`, which come
from `Model.get_absolute_url()` by default. You can override the URL
specifically for notifications by implementing
`Model.get_url_for_notifications(notification, request)` on the related
model.

Query string arguments (list endpoints):

- **max** — maximum length of the returned list.
- **mark_as_read** — if truthy, mark the returned notifications as read.

Example: `GET api/unread_list/?max=3&mark_as_read=true` returns three
notifications and marks them read, so they'll drop off the next request.

> **Security note:** the state-changing views (`mark_as_read`,
> `mark_as_unread`, `mark_all_as_read`, `delete`) require POST and a CSRF
> token. Only the list-with-`mark_as_read` query parameter above is
> accessible via GET, and it's gated to the requesting user's own unread
> rows.

### Wiring it up

1. Load `{% load notifications_tags %}` in the template.
2. Include the JS and register the callbacks:

    ```django
    <script src="{% static 'notifications/notify.js' %}"></script>
    {% register_notify_callbacks callbacks='fill_notification_list,fill_notification_badge' %}
    ```

    Since 1.11.2, `register_notify_callbacks` renders its configuration as
    a `<script type="application/json">` block rather than inline JS, so it
    works under strict Content Security Policies without a `'unsafe-inline'`
    allowance.

    `register_notify_callbacks` arguments:

    - `badge_class` (default `live_notify_badge`) — CSS class of the unread-count element.
    - `menu_class` (default `live_notify_list`) — CSS class of the list element.
    - `refresh_period` (default `15`) — poll interval in seconds.
    - `fetch` (default `5`) — how many notifications to fetch each poll.
    - `callbacks` (default `''`) — comma-separated list of JS functions to call on each poll.
    - `api_name` (default `list`) — either `list` or `count`.
    - `mark_as_read` (default `False`) — mark fetched notifications as read.
    - `nonce` (default `None`) — if set, emitted as the `nonce` attribute
      on the `<script>` tag, for strict CSP setups that allow JSON blocks
      by nonce.

3. Insert a live-updating badge:

    ```django
    {% live_notify_badge %}
    ```

    Takes `badge_class` (default `live_notify_badge`) — CSS class for the
    generated `<span>`.

4. Insert a live-updating list:

    ```django
    {% live_notify_list %}
    ```

    Takes `list_class` (default `live_notify_list`) — CSS class for the
    generated `<ul>`.

### Using the live-updater with Bootstrap

Reuse the template tags with Bootstrap's classes:

```django
{% live_notify_badge badge_class="badge" %}
{% live_notify_list list_class="dropdown-menu" %}
```

### Custom JavaScript callbacks

The `callbacks` argument of `register_notify_callbacks` is a comma-separated
list of JS function names called on every poll. Each function receives one
argument, `data`, containing the entire API response.

```django
{% register_notify_callbacks callbacks='fill_notification_badge,my_special_notification_callback' %}
```

```javascript
function my_special_notification_callback(data) {
    for (const msg of data.unread_list) {
        console.log(msg);
    }
}
```

### Testing the live-updater

1. Clone the repo.
2. Run `python manage.py runserver`.
3. Browse to `http://127.0.0.1:8000/test/`.
4. Click "Make a notification" — a new notification should appear in the
   list within 5-10 seconds.

## Serializing the notification model

See the DRF guide on
[generic relationships](https://www.django-rest-framework.org/api-guide/relations/#generic-relationships).
The example below picks a serializer based on the target type:

```python
class GenericNotificationRelatedField(serializers.RelatedField):

    def to_representation(self, value):
        if isinstance(value, Foo):
            return FooSerializer(value).data
        if isinstance(value, Bar):
            return BarSerializer(value).data


class NotificationSerializer(serializers.Serializer):
    recipient = PublicUserSerializer(read_only=True)
    unread = serializers.BooleanField(read_only=True)
    target = GenericNotificationRelatedField(read_only=True)
```

Thanks to @DaWy.

## AbstractNotification model

If you need to extend the notification model with extra fields, subclass
`AbstractNotification`:

```python
# your_app/models.py
from django.db import models
from notifications.base.models import AbstractNotification


class Notification(AbstractNotification):
    category = models.ForeignKey('myapp.Category', on_delete=models.CASCADE)

    class Meta(AbstractNotification.Meta):
        abstract = False
```

Then point the library at your model in `settings.py`:

```python
NOTIFICATIONS_NOTIFICATION_MODEL = 'your_app.Notification'
```

As of 1.11.3, swapping is resolved via Django's built-in app loading rather
than the third-party `swapper` package. No configuration changes are
required when upgrading.

## Notes

### Email notifications

Email delivery is not built in. The `Notification.emailed` field is
reserved to make it easier to track whether you've sent one.

### Bulk creation and signals

As of 1.11.0, `notify.send()` uses `bulk_create`, which means Django's
`post_save` signal does **not** fire for the `Notification` rows it writes.

If you previously relied on `post_save` to trigger side effects (email,
push, etc.), switch to connecting the `notify` signal instead:

```python
from notifications.signals import notify

def handle_notifications(sender, verb, **kwargs):
    recipient = kwargs.get('recipient')
    # side effect here (send email, push, ...)

notify.connect(handle_notifications)
```

The `notify` signal fires once per `notify.send()` call, *before* the rows
are written. If you need access to the saved `Notification` objects, use
the return value of `notify.send()` instead:

```python
from notifications.signals import notify

responses = notify.send(
    sender=user,
    recipient=target_user,
    verb='commented on',
    target=post,
)

# Each response is a (handler_function, return_value) tuple.
# The default handler returns the list of created Notification objects.
for handler, notifications in responses:
    for notification in notifications:
        send_push(notification.recipient, str(notification))
```

### Sample app

A sample app lives at `notifications/tests/sample_notifications` and
exercises the `AbstractNotification` swap path. Run it by exporting
`SAMPLE_APP=1`:

```bash
export SAMPLE_APP=1
python manage.py runserver
unset SAMPLE_APP
```

## Credits

### Upstream contributors

The original `django-notifications` was built by (alphabetical):

- [Alvaro Leonel](https://github.com/AlvaroLQueiroz)
- [Federico Capoano](https://github.com/nemesisdesign)
- [Samuel Spencer](https://github.com/LegoStormtroopr)
- [Yang Yubo](https://github.com/yangyubo)
- [YPCrumble](https://github.com/YPCrumble)
- [Zhongyuan Zhang](https://github.com/zhang-z)

See [`AUTHORS.txt`](AUTHORS.txt) for the full contributor list.

### Fork maintainers

This community fork is maintained by
[django-notifications-community contributors](https://github.com/django-notifications-community/django-notifications-community/graphs/contributors).
Please use this repo's issue tracker for fork-specific bugs and features
rather than contacting the upstream authors.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, testing,
and pull request guidelines.
