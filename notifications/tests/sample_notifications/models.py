from django.db import models

from notifications.base.models import AbstractNotification


class Tag(models.Model):
    name = models.CharField(max_length=32)

    def __str__(self):
        return self.name


class Notification(AbstractNotification):
    details = models.CharField(max_length=64, blank=True, null=True)  # noqa: DJ001
    attachment = models.FileField(upload_to='attachments/', blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='notifications')

    class Meta(AbstractNotification.Meta):
        abstract = False
