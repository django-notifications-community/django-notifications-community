"""Resolve the Notification model, honoring ``NOTIFICATIONS_NOTIFICATION_MODEL``.

Same convention as ``AUTH_USER_MODEL``: users point the setting at
their own model (e.g. ``"my_app.Notification"``) to swap it in.
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
