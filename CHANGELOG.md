# Changelog

## Community fork

This project is now maintained as a community fork at
[`django-notifications-community/django-notifications-community`](https://github.com/django-notifications-community/django-notifications-community)
and published to PyPI as `django-notifications-community`. See
[upstream issue #416](https://github.com/django-notifications/django-notifications/issues/416)
for background on why the fork exists.

## Unreleased

  - Fixed `notify.send(..., data={...})` silently producing
    `Notification.data == {}`. The handler's data-merging loop was
    setting the caller's payload via `setattr` and then immediately
    clobbering it with an empty dict. Explicit `data=` now survives
    and merges with any extra kwargs.
  - Fixed `notify.send(..., timestamp=None)` raising `IntegrityError`
    on the `NOT NULL` `timestamp` column. `kwargs.pop('timestamp',
    timezone.now())` returned `None` when the caller passed `None`
    explicitly (the default only kicks in when the key is absent).
    Coerce a `None` to `timezone.now()`.
  - Hoisted `ContentType.objects.get_for_model()` for the actor and the
    optional `target` / `action_object` out of the per-recipient loop
    in `notify_handler`. The lookups are independent of the recipient,
    so a 500-user group call now does at most three lookups instead of
    up to 1500. `get_for_model` is process-cached, but the saved
    overhead still adds up under cold-cache or high-throughput
    conditions.

## 1.12.0 (2026-04-30)

  - Dropped support for Django 4.2 and 5.1. Both are past end of
    upstream support (5.1 in December 2025, 4.2 in April 2026). Users
    still on 4.2 or 5.1 should pin
    `django-notifications-community<1.12`.
  - Relaxed the Django upper bound to `<6.3` (was `<5.3`) so users can
    install on Django 6.0, 6.1, and the upcoming 6.2 LTS without
    waiting for a release.
  - Added Django 6.0 to the CI matrix on Python 3.12 and 3.13 (6.0
    requires Python 3.12+). The tested matrix is now Django 5.2 LTS on
    Python 3.10 through 3.13, plus Django 6.0 on Python 3.12 and 3.13.
  - As a side effect, the `RemovedInDjango51Warning: 'index_together' is
    deprecated` that used to fire on every `migrate` under Django 4.2 no
    longer appears.
  - Added a small extension hook registry at `notifications.registry`
    (`apply_queryset_filters`, `derive_cache_key`,
    `collect_invalidation_keys`). Companion packages can register
    callbacks instead of forking views, helpers, or template tags;
    with nothing registered the hooks are no-ops and behaviour is
    unchanged. (#51)
  - Added a `sites` optional extra:
    `pip install "django-notifications-community[sites]"` pulls in
    `django-notifications-community-sites`, which scopes notifications
    to the current site via the new hook registry. See the
    [Multi-site](README.md#multi-site) section of the README for
    details.

## 1.11.3 (2026-04-15)

Final release of the 1.11.x line.

  - Replaced `django-model-utils` `Choices` with `TextChoices` for
    `Notification.LEVELS` (#42, thanks @PanovYury)
  - Dropped the `swapper` runtime dependency; `AbstractNotification`
    swapping now uses Django's built-in app loading (#45)
  - Expanded the `bulk_create` migration guide in the README

  No migrations. Drop-in upgrade from 1.11.x.

## 1.11.2 (2026-04-12)

  - Fixed `format_html` placeholder usage in template tags and Django
    5.x compatibility (#37)
  - `register_notify_callbacks` now renders its config as a
    `<script type="application/json">` block, avoiding quoting bugs and
    working under strict CSPs (#37)
  - Removed remaining Django < 4.2 compatibility shims (#34)
  - Modernized `notify.js` syntax; removed stray utf-8 coding headers
    (#33)
  - Docs: updated README and CONTRIBUTING for `uv` (#32)
  - Tooling: added Dependabot and pre-commit; removed `pylint`,
    `prospector`, and `MANIFEST.in`
  - Tests: expanded coverage for template tags, helpers, admin, and API
    URL resolution (#35, #38, #39)

## 1.11.1 (2026-04-12)

  - Removed dead Python 2 and Django < 2.0 compatibility code (#24)
  - `USE_JSONFIELD` setting is now evaluated at call time instead of
    import time, so runtime overrides work correctly (#25)
  - API serialization now includes `id` and `timestamp` fields that were
    previously silently dropped by `model_to_dict` (#26)
  - Added ruff configuration and applied initial formatting pass (#27)
  - Suppressed DJ001 lint for intentionally nullable string fields (#28)

  No behavior changes.

## 1.11.0 (2026-04-12)

  - Fixed attribute typos in `action_object_url()` that would raise
    `AttributeError` whenever the method was called (#15)
  - Restored `assert_soft_delete()` error message that was left as a
    placeholder string (#16)
  - Fixed unread notification count cache leaking across users due to a
    shared cache key (#17)
  - Excluded soft deleted notifications from API count and list endpoints
    when `SOFT_DELETE` is enabled (#18)
  - State changing views (`mark_as_read`, `mark_as_unread`,
    `mark_all_as_read`, `delete`) now require POST requests. GET requests
    return 405 Method Not Allowed. The bundled `notice.html` template has
    been updated accordingly. (#19)
  - `mark_as_read()`, `mark_as_unread()`, and the soft delete view now pass
    `update_fields` to `save()`, reducing write amplification and avoiding
    race conditions with concurrent updates (#20)
  - `get_notification_list` now marks notifications as read with a single
    bulk UPDATE instead of one `save()` per row (#21)
  - `notify_handler` now uses `bulk_create` instead of one `save()` per
    recipient (#22)

  **Potentially breaking changes:**

  - Views that previously accepted GET now require POST. Templates and
    client code that use `<a>` links to mark/delete endpoints must switch
    to `<form method="post">` with `{% csrf_token %}`.
  - `bulk_create` does not fire `post_save` signals. If you have registered
    `post_save` handlers on the `Notification` model, they will no longer
    fire when notifications are created via `notify.send()`.

## 1.10.0 (2026-04-12)

  - Fixed `notify_handler` kwargs mutation across multiple recipients: custom
    model fields and JSON data were silently lost for all recipients after the
    first (#3)
  - Replaced unmaintained `jsonfield` package with Django's built-in
    `models.JSONField` (available since Django 3.1). Existing migrations are
    shimmed so upgrades work whether or not `jsonfield` is still installed (#4)
  - Added composite database indexes on `(content_type, object_id)` for all
    three GenericForeignKey pairs (actor, target, action_object), speeding up
    cascade deletes and reverse lookups on large tables (#5)
  - Added `select_related` / `prefetch_related` to notification list views and
    the JSON API helper, eliminating N+1 query patterns (#6)
  - Removed `jsonfield` from dependencies
  - Dropped support for Python 3.9 (already declared in 1.9.0 metadata but
    not enforced)

  **Migrations:** This release includes two new migrations (0011, 0012).
  Run `python manage.py migrate` after upgrading.

## 1.9.0 (community fork release, 2026-04-11)

First release published by the community fork. Code contents are identical to
upstream `django-notifications/django-notifications` `master` at the point of
forking, with no functional changes to the `notifications` package. The goal
of this release is to put the unreleased 1.9.0 work onto PyPI so users can
consume the Django 5.x and Python 3.13 support that was stuck unreleased
upstream.

Fork-specific changes:

  - Published upstream's unreleased 1.9.0 to PyPI as `django-notifications-community`
  - Migrated packaging from `setup.py` + `setup.cfg` to `pyproject.toml` (PEP 621)
  - Corrected SPDX license metadata to `BSD-3-Clause` (matches `LICENSE.txt`; upstream `setup.py` incorrectly declared `MIT`)
  - Refreshed CI matrix to Django 4.2 / 5.1 / 5.2 x Python 3.10 / 3.11 / 3.12 / 3.13 on `ubuntu-latest`
  - Dropped vestigial `.travis.yml`
  - Added `CONTRIBUTING.md` and `SECURITY.md`

Upstream 1.9.0 content (unchanged):

  - Added support for Django 5.0, 5.1, and 5.2
  - Added support for Python 3.12 and 3.13
  - Dropped support for Django < 4.2
  - Dropped support for Python < 3.9
  - Fixed distutils deprecation

## 1.8.3

  - Fixes missing static folder/files

## 1.8.2

  - Added the migration for verbose_name changes

## 1.8.0

  - Added support for Django 4.1
  - Dropped support for Django < 3.2 and Python < 3.7
  - Added indexes for GenericForeignKey fields in AbstractNotificationModel (see https://docs.djangoproject.com/en/4.1/ref/contrib/contenttypes/#generic-relations)
  - new setting 'CACHE_TIMEOUT' to cache certain result such as "notifications.unread().count".
  (a timeout value of 0 won’t cache anything).
  - #263 Fix vunerability in views
  - #233 Adds methods to convert to human readable type
  - Translate project all strings

## 1.7.0

  - Added support for Django 3.2 and Django 4.0
  - Fixed bug on IE11 for using `forEach` in notify.js

## 1.6.0

  - Added support to Django up to version 3.0
  - Added `AbstractNotification` model
  - Added prefetch for actor field in admin
  - Added never\_cache to some views to avoid no-update bug

## 1.5

Now all configs for the app are made inside the dictionary
*DJANGO\_NOTIFICATION\_CONFIG* in *settings.py*.

Default configs: `` `Python DJANGO_NOTIFICATIONS_CONFIG = {
'PAGINATE_BY': 20, 'USE_JSONFIELD': False, 'SOFT_DELETE': False,
'NUM_TO_FETCH': 10, } ``\`

  - Improve code quality. (@AlvaroLQueiroz)
  - Improve url patterns and remove duplicated code. (@julianogouveia)
  - Added a view for show all notifications. \#205 (@AlvaroLQueiroz)
  - Added a new tag to verify if an user has unread notifications. \#164
    (@AlvaroLQueiroz)
  - Improve documentation. (@pandabearcoder)
  - Fix pagination in list views. \#69 (@AlvaroLQueiroz)
  - Improve test matrix. (@AlvaroLQueiroz)

## 1.4

  - Adds support for django 2.0.0 (@jphamcsp and @nemesisdesign).
  - Adds database index for some fields (@nemesisdesign).
  - Changes the ID-based selection to a class-based selection in the
    methods
    \_\_[live\_notify\_badge](THIS%20VERSION%20HAS%20BREAKING%20CHANGES__:)
    and \_\_live\_notify\_list\_\_ (@AlvaroLQueiroz).
  - Now extra data and slug are returned on
    \_\_live\_unread\_notification\_list\_\_ API (@AlvaroLQueiroz).
  - Fix documentation issues (@archatas, @yaoelvon and @AlvaroLQueiroz).

## 1.3

  - Redirect to unread view after mark as read. (@osminogin)
  - Django 1.10 compability. (@osminogin)
  - Django Admin overhead reduction by removing the need to carry all
    recipients users. (@theromis)
  - Added option to mark as read in
    \_\_live\_unread\_notification\_list\_\_ endpoint. (@osminogin)
  - Fixed parameter name error in README.rst: there is no
    \_\_api\_url\_name\_\_ parameter, the correct name is
    \_\_api\_name\_\_ (@ikkebr)
  - Added \_\_sent()\_\_, \_\_unsent()\_\_, \_\_mark\_as\_sent()\_\_ and
    \_\_mark\_as\_unsent()\_\_ methods in the queryset. (@theromis)
  - \_\_notify.send()\_\_ now returns the list of saved Notifications
    instances. (@satyanash)
  - Now \_\_recipient\_\_ can be a User queryset. (@AlvaroLQueiroz)
  - Fix XMLHttpRequest onready event handler. (@AlvaroLQueiroz)

## 1.2

  - Django 1.9 template tag compatibility: due to `register.simple_tag`
    automatically espacing `unsafe_html` in Django 1.9, it is now
    recommended to use format\_html (@ikkebr)
  - Fixed parameter name error in README.rst: there is no to\_fetch
    parameter, the correct name is fetch (@ikkebr)
  - Add missing migration (@marcgibbons)
  - Minor documentation correction (@tkwon, @zhang-z)
  - Return updated count in QuerySet (@zhang-z)

## 1.1

  - Custom now() invocation got overlooked by PR \#113 (@yangyuvo)
  - Added sentinals for unauthenticated users, preventing a 500 error
    (@LegoStormtroopr)
  - Fix: Mark All As read fails if soft-deleted \#126 (@zhang-z)

## 1.0

The first major version that requires Django 1.7+.

  - Drop support for Django 1.6 and below (@zhang-z)
  - Django 1.9 compability (@illing2005)
  - Now depends on Django built-in migration facility,
    "south\_migrations" dependence was removed (@zhang-z)
  - Make django-notification compatible with django-model-utils \>= 2.4
    ( \#87, \#88, \#90 ) (@zhang-z)
  - Fix a RemovedInDjango110Warning in unittest (@zhang-z)
  - Fix pep8 & use setuptools (@areski)
  - Fix typo- in doc (@areski, @zhang-z)
  - Add app\_name in urls.py (@zhang-z)
  - Use Django's vendored copy of six (@funkybob)
  - Tidy with flake8 (@funkybob)
  - Remove custom now() function (@funkybob, @yangyubo)
  - notify.send() accepts User or Group (@Evidlo)

## 0.8.0

0.8 is the last major version supports Django 1.4\~1.6, version 0.8.0
will go into bugfix mode, no new features will be accepted.

  - Bugfixes for live-updater, and added a live tester page
    (@LegoStormtroopr)
  - Class-based classes (@alazaro)
  - Fixed urls in tests (@alazaro)
  - Added app\_label to Notification model in order to fix a Django 1.9
    deprecation warning (@Heldroe)
  - django-model-utils compatible issue (must \>=2.0.3 and \<2.4)
    (@zhang-z)
  - Reliable setup.py versioning (@yangyubo)

## 0.7.1

  - Able to pass level when adding notification (@Arthur)
  - Fix deprecation notice in Django 1.8 (@ashokfernandez)
  - Fix Python 3 support for notification model (@philroche)
  - Bugfix for wrong user unread notification count (@Geeknux)
  - A simple javascript API for live-updating specific fields within a
    django template (@LegoStormtroopr)
  - Add missing migration for Notification model (@shezadkhan137)

## 0.7.0

  - Add filters and displays to Django model Admin
  - Support Django 1.8, compatible with both django-south (django \<
    1.7) and built-in schema migration (django \>= 1.7)
  - Compatible with Python 3
  - Test fixtures, and integrated with travis-ci

## 0.6.2

  - Fix README.rst reStructuredText syntax format
  - Use relative imports
  - Add contributors to AUTHORS.txt

## 0.6.1

  - Add support for custom user model
  - mark\_as\_unread
  - Require django-model-utils \>= 2.0.3
  - Use different <span class="title-ref">now</span> function according
    to the <span class="title-ref">USE\_TZ</span> setting

## 0.6.0

  - Improve documentation
  - Add unicode support at admin panel or shell

## 0.5.5

Support for arbitrary data attribute.

## 0.5.1

Fix package descriptions and doc links.

## 0.5

First version based on
[django-activity-stream](https://github.com/justquick/django-activity-stream)
v0.4.3
