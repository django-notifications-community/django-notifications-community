"""Django notifications apps file"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class Config(AppConfig):
    name = 'notifications'
    verbose_name = _('Notifications')
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        super().ready()
        # backwards compatibility: expose notify on the package
        import notifications
        from notifications.base.models import notify_handler
        from notifications.signals import notify
        notifications.notify = notify

        notify.connect(notify_handler, dispatch_uid='notifications.models.notification')
