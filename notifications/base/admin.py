from django.contrib import admin
from django.utils.translation import gettext_lazy as _


@admin.action(description=_('Mark selected notifications as unread'))
def mark_unread(modeladmin, request, queryset):
    queryset.update(unread=True)


class AbstractNotificationAdmin(admin.ModelAdmin):
    raw_id_fields = ('recipient',)
    readonly_fields = ('action_object_url', 'actor_object_url', 'target_object_url')
    list_display = ('recipient', 'actor', 'level', 'target', 'unread', 'public')
    list_filter = (
        'level',
        'unread',
        'public',
        'timestamp',
    )
    actions = [mark_unread]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('actor', 'action_object', 'target')
