"""Django notifications apps file"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class Config(AppConfig):
    name = 'notifications'
    verbose_name = _('Notifications')
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        super().ready()
        # this is for backwards compatibility
        import notifications.signals

        notifications.notify = notifications.signals.notify
