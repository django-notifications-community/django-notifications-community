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

    # Since Django 6.1 the short_description on the fields no longer reaches the admin, so the columns live here.
    @admin.display(description=_('actor'))
    def actor(self, obj):
        return obj.actor

    @admin.display(description=_('target'))
    def target(self, obj):
        return obj.target

    @admin.display(description=_('action object'))
    def action_object(self, obj):
        return obj.action_object
