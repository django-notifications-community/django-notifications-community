"""Django Notifications example views"""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.encoding import iri_to_uri
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from notifications import settings as notification_settings
from notifications.helpers import get_notification_list, invalidate_unread_count_cache
from notifications.registry import apply_queryset_filters
from notifications.swappable import load_notification_model
from notifications.utils import slug2id

Notification = load_notification_model()


class NotificationViewList(LoginRequiredMixin, ListView):
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = notification_settings.get_config()['PAGINATE_BY']


class AllNotificationsList(NotificationViewList):
    """
    Index page for authenticated user
    """

    def get_queryset(self):
        if notification_settings.get_config()['SOFT_DELETE']:
            qset = self.request.user.notifications.active()
        else:
            qset = self.request.user.notifications.all()
        qset = apply_queryset_filters(qset, self.request)
        return qset.select_related(
            'actor_content_type', 'target_content_type', 'action_object_content_type'
        ).prefetch_related('actor', 'target', 'action_object')


class UnreadNotificationsList(NotificationViewList):
    def get_queryset(self):
        qset = apply_queryset_filters(self.request.user.notifications.unread(), self.request)
        return qset.select_related(
            'actor_content_type', 'target_content_type', 'action_object_content_type'
        ).prefetch_related('actor', 'target', 'action_object')


@require_POST
@login_required
def mark_all_as_read(request):
    apply_queryset_filters(request.user.notifications.all(), request).mark_all_as_read()
    invalidate_unread_count_cache(request.user, request)

    _next = request.POST.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))
    return redirect('notifications:unread')


@require_POST
@login_required
def mark_as_read(request, slug=None):
    notification_id = slug2id(slug)

    qs = apply_queryset_filters(Notification.objects.all(), request)
    notification = get_object_or_404(qs, recipient=request.user, id=notification_id)
    notification.mark_as_read()
    invalidate_unread_count_cache(request.user, request)

    _next = request.POST.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect('notifications:unread')


@require_POST
@login_required
def mark_as_unread(request, slug=None):
    notification_id = slug2id(slug)

    qs = apply_queryset_filters(Notification.objects.all(), request)
    notification = get_object_or_404(qs, recipient=request.user, id=notification_id)
    notification.mark_as_unread()
    invalidate_unread_count_cache(request.user, request)

    _next = request.POST.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect('notifications:unread')


@require_POST
@login_required
def delete(request, slug=None):
    notification_id = slug2id(slug)

    qs = apply_queryset_filters(Notification.objects.all(), request)
    notification = get_object_or_404(qs, recipient=request.user, id=notification_id)

    if notification_settings.get_config()['SOFT_DELETE']:
        notification.deleted = True
        notification.save(update_fields=['deleted'])
    else:
        notification.delete()
    invalidate_unread_count_cache(request.user, request)

    _next = request.POST.get('next')

    if _next and url_has_allowed_host_and_scheme(_next, settings.ALLOWED_HOSTS):
        return redirect(iri_to_uri(_next))

    return redirect('notifications:all')


@never_cache
def live_unread_notification_count(request):
    user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {'unread_count': 0}
    else:
        data = {
            'unread_count': apply_queryset_filters(request.user.notifications.unread(), request).count(),
        }
    return JsonResponse(data)


@never_cache
def live_unread_notification_list(request):
    """Return a json with a unread notification list"""
    user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {'unread_count': 0, 'unread_list': []}
        return JsonResponse(data)

    unread_list = get_notification_list(request, 'unread')

    data = {
        'unread_count': apply_queryset_filters(request.user.notifications.unread(), request).count(),
        'unread_list': unread_list,
    }
    return JsonResponse(data)


@never_cache
def live_all_notification_list(request):
    """Return a json with a unread notification list"""
    user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {'all_count': 0, 'all_list': []}
        return JsonResponse(data)

    all_list = get_notification_list(request)

    data = {'all_count': _all_notification_qs(request).count(), 'all_list': all_list}
    return JsonResponse(data)


def live_all_notification_count(request):
    user_is_authenticated = request.user.is_authenticated

    if not user_is_authenticated:
        data = {'all_count': 0}
    else:
        data = {
            'all_count': _all_notification_qs(request).count(),
        }
    return JsonResponse(data)


def _all_notification_qs(request):
    """Return the 'all notifications' queryset, excluding soft-deleted when enabled."""
    qs = apply_queryset_filters(request.user.notifications.all(), request)
    if notification_settings.get_config()['SOFT_DELETE']:
        return qs.active()
    return qs
