from django.contrib import admin

from notifications.base.admin import AbstractNotificationAdmin
from notifications.swappable import load_notification_model

Notification = load_notification_model()


@admin.register(Notification)
class NotificationAdmin(AbstractNotificationAdmin):
    pass
