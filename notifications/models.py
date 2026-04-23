from .base.models import AbstractNotification, notify_handler  # noqa
from .swappable import NOTIFICATION_MODEL_SETTING


class Notification(AbstractNotification):
    class Meta(AbstractNotification.Meta):
        abstract = False
        swappable = NOTIFICATION_MODEL_SETTING
