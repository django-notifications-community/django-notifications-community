"""Internal helpers for the swappable Notification model.

Users configure the swap by pointing
``NOTIFICATIONS_NOTIFICATION_MODEL`` at their own model in settings,
e.g. ``"my_app.Notification"``. This mirrors the convention Django
itself uses for ``AUTH_USER_MODEL``: a single setting read lazily via
``getattr`` so that ``@override_settings`` keeps working in tests.
"""
from django.apps import apps
from django.conf import settings

NOTIFICATION_MODEL_SETTING = "NOTIFICATIONS_NOTIFICATION_MODEL"
DEFAULT_NOTIFICATION_MODEL = "notifications.Notification"


def load_notification_model():
    """Return the configured Notification model class."""
    model_path = getattr(
        settings, NOTIFICATION_MODEL_SETTING, DEFAULT_NOTIFICATION_MODEL
    )
    return apps.get_model(model_path)
