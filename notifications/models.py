from .base.models import AbstractNotification, notify_handler  # noqa
from .swappable import NOTIFICATION_MODEL_SETTING


class Notification(AbstractNotification):
    class Meta(AbstractNotification.Meta):
        abstract = False
        swappable = NOTIFICATION_MODEL_SETTING

    def naturalday(self):
        """
        Shortcut for the ``humanize``.
        Take a parameter humanize_type. This parameter control the which humanize method use.
        Return ``today``, ``yesterday`` ,``now``, ``2 seconds ago``etc.
        """
        from django.contrib.humanize.templatetags.humanize import naturalday

        return naturalday(self.timestamp)

    def naturaltime(self):
        from django.contrib.humanize.templatetags.humanize import naturaltime

        return naturaltime(self.timestamp)
