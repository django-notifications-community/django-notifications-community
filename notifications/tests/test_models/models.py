from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models

from notifications.base.models import AbstractNotification


class Customer(models.Model):
    name = models.CharField(max_length=64)
    address = models.TextField()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'foo/{self.id}/'


class TargetObject(Customer):
    def get_url_for_notifications(self, notification, request):
        return f'bar/{self.id}/'


class Category(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class CategorizedNotification(AbstractNotification):
    """Custom model with a non-nullable foreign key, as the README documents.

    ``AbstractNotification`` hardcodes its ``related_name`` values, so the four
    relations that clash with ``notifications.Notification`` are redeclared
    with distinct accessor names.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categorized_notifications',
    )
    actor_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name='categorized_notify_actor'
    )
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='categorized_notify_target',
        blank=True,
        null=True,
    )
    action_object_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='categorized_notify_action_object',
        blank=True,
        null=True,
    )

    category = models.ForeignKey('test_models.Category', on_delete=models.CASCADE)

    class Meta(AbstractNotification.Meta):
        abstract = False
