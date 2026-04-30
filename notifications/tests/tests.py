"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".
Replace this with more appropriate tests for your application.
"""

import json
from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.template import Context, Template
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import localtime

from notifications.base.models import notify_handler
from notifications.helpers import get_num_to_fetch, get_object_url
from notifications.signals import notify
from notifications.swappable import load_notification_model
from notifications.tests.test_models.models import Customer, TargetObject
from notifications.utils import id2slug, slug2id

Notification = load_notification_model()

MALICIOUS_NEXT_URLS = [
    'http://bla.com',
    'http://www.bla.com',
    'https://bla.com',
    'https://www.bla.com',
    'ftp://www.bla.com/file.exe',
]


class NotificationTest(TestCase):
    """Django notifications automated tests"""

    @override_settings(USE_TZ=True)
    @override_settings(TIME_ZONE='Asia/Shanghai')
    def test_use_timezone(self):
        from_user = User.objects.create(username='from', password='pwd', email='example@example.com')
        to_user = User.objects.create(username='to', password='pwd', email='example@example.com')
        notify.send(from_user, recipient=to_user, verb='commented', action_object=from_user)
        notification = Notification.objects.get(recipient=to_user)
        delta = timezone.now().replace(tzinfo=dt_timezone.utc) - localtime(
            notification.timestamp, ZoneInfo(settings.TIME_ZONE)
        )
        self.assertTrue(delta.seconds < 60)
        # The delta between the two events will still be less than a second despite the different timezones
        # The call to now and the immediate call afterwards will be within a short period of time, not 8 hours as the
        # test above was originally.

    @override_settings(USE_TZ=False)
    @override_settings(TIME_ZONE='Asia/Shanghai')
    def test_disable_timezone(self):
        from_user = User.objects.create(username='from2', password='pwd', email='example@example.com')
        to_user = User.objects.create(username='to2', password='pwd', email='example@example.com')
        notify.send(from_user, recipient=to_user, verb='commented', action_object=from_user)
        notification = Notification.objects.get(recipient=to_user)
        delta = timezone.now() - notification.timestamp
        self.assertTrue(delta.seconds < 60)

    def test_humanize_naturalday_timestamp(self):
        from_user = User.objects.create(username='from2', password='pwd', email='example@example.com')
        to_user = User.objects.create(username='to2', password='pwd', email='example@example.com')
        notify.send(from_user, recipient=to_user, verb='commented', action_object=from_user)
        notification = Notification.objects.get(recipient=to_user)
        self.assertEqual(notification.naturalday(), 'today')

    def test_humanize_naturaltime_timestamp(self):
        from_user = User.objects.create(username='from2', password='pwd', email='example@example.com')
        to_user = User.objects.create(username='to2', password='pwd', email='example@example.com')
        notify.send(from_user, recipient=to_user, verb='commented', action_object=from_user)
        notification = Notification.objects.get(recipient=to_user)
        self.assertEqual(notification.naturaltime(), 'now')


class NotificationManagersTest(TestCase):
    """Django notifications Manager automated tests"""

    def setUp(self):
        self.message_count = 10
        self.other_user = User.objects.create(username='other1', password='pwd', email='example@example.com')

        self.from_user = User.objects.create(username='from2', password='pwd', email='example@example.com')
        self.to_user = User.objects.create(username='to2', password='pwd', email='example@example.com')
        self.to_group = Group.objects.create(name='to2_g')
        self.to_user_list = User.objects.all()
        self.to_group.user_set.add(self.to_user)
        self.to_group.user_set.add(self.other_user)

        for _ in range(self.message_count):
            notify.send(self.from_user, recipient=self.to_user, verb='commented', action_object=self.from_user)
        # Send notification to group
        notify.send(self.from_user, recipient=self.to_group, verb='commented', action_object=self.from_user)
        self.message_count += self.to_group.user_set.count()
        # Send notification to user list
        notify.send(self.from_user, recipient=self.to_user_list, verb='commented', action_object=self.from_user)
        self.message_count += len(self.to_user_list)

    def test_notify_send_return_val(self):
        results = notify.send(self.from_user, recipient=self.to_user, verb='commented', action_object=self.from_user)
        for result in results:
            if result[0] is notify_handler:
                self.assertEqual(len(result[1]), 1)
                # only check types for now
                self.assertEqual(type(result[1][0]), Notification)

    def test_notify_send_return_val_group(self):
        results = notify.send(self.from_user, recipient=self.to_group, verb='commented', action_object=self.from_user)
        for result in results:
            if result[0] is notify_handler:
                self.assertEqual(len(result[1]), self.to_group.user_set.count())
                for notification in result[1]:
                    # only check types for now
                    self.assertEqual(type(notification), Notification)

    def test_unread_manager(self):
        self.assertEqual(Notification.objects.unread().count(), self.message_count)
        notification = Notification.objects.filter(recipient=self.to_user).first()
        notification.mark_as_read()
        self.assertEqual(Notification.objects.unread().count(), self.message_count - 1)
        for notification in Notification.objects.unread():
            self.assertTrue(notification.unread)

    def test_read_manager(self):
        self.assertEqual(Notification.objects.unread().count(), self.message_count)
        notification = Notification.objects.filter(recipient=self.to_user).first()
        notification.mark_as_read()
        self.assertEqual(Notification.objects.read().count(), 1)
        for notification in Notification.objects.read():
            self.assertFalse(notification.unread)

    def test_mark_all_as_read_manager(self):
        self.assertEqual(Notification.objects.unread().count(), self.message_count)
        Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
        self.assertEqual(self.to_user.notifications.unread().count(), 0)

    @override_settings(DJANGO_NOTIFICATIONS_CONFIG={'SOFT_DELETE': True})
    def test_mark_all_as_read_manager_with_soft_delete(self):
        # even soft-deleted notifications should be marked as read
        # refer: https://github.com/django-notifications/django-notifications/issues/126
        to_delete = Notification.objects.filter(recipient=self.to_user).order_by('id')[0]
        to_delete.deleted = True
        to_delete.save()
        self.assertTrue(Notification.objects.filter(recipient=self.to_user).order_by('id')[0].unread)
        Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
        self.assertFalse(Notification.objects.filter(recipient=self.to_user).order_by('id')[0].unread)

    def test_mark_all_as_unread_manager(self):
        self.assertEqual(Notification.objects.unread().count(), self.message_count)
        Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
        self.assertEqual(self.to_user.notifications.unread().count(), 0)
        Notification.objects.filter(recipient=self.to_user).mark_all_as_unread()
        self.assertEqual(Notification.objects.unread().count(), self.message_count)

    def test_mark_all_deleted_manager_without_soft_delete(self):
        self.assertRaises(ImproperlyConfigured, Notification.objects.active)
        self.assertRaises(ImproperlyConfigured, Notification.objects.active)
        self.assertRaises(ImproperlyConfigured, Notification.objects.mark_all_as_deleted)
        self.assertRaises(ImproperlyConfigured, Notification.objects.mark_all_as_active)

    @override_settings(DJANGO_NOTIFICATIONS_CONFIG={'SOFT_DELETE': True})
    def test_mark_all_deleted_manager(self):
        notification = Notification.objects.filter(recipient=self.to_user).first()
        notification.mark_as_read()
        self.assertEqual(Notification.objects.read().count(), 1)
        self.assertEqual(Notification.objects.unread().count(), self.message_count - 1)
        self.assertEqual(Notification.objects.active().count(), self.message_count)
        self.assertEqual(Notification.objects.deleted().count(), 0)

        Notification.objects.mark_all_as_deleted()
        self.assertEqual(Notification.objects.read().count(), 0)
        self.assertEqual(Notification.objects.unread().count(), 0)
        self.assertEqual(Notification.objects.active().count(), 0)
        self.assertEqual(Notification.objects.deleted().count(), self.message_count)

        Notification.objects.mark_all_as_active()
        self.assertEqual(Notification.objects.read().count(), 1)
        self.assertEqual(Notification.objects.unread().count(), self.message_count - 1)
        self.assertEqual(Notification.objects.active().count(), self.message_count)
        self.assertEqual(Notification.objects.deleted().count(), 0)


class NotificationTestPages(TestCase):
    """Django notifications automated page tests"""

    def setUp(self):
        self.message_count = 10
        self.from_user = User.objects.create_user(username='from', password='pwd', email='example@example.com')
        self.to_user = User.objects.create_user(username='to', password='pwd', email='example@example.com')
        self.to_user.is_staff = True
        self.to_user.save()
        for _ in range(self.message_count):
            notify.send(self.from_user, recipient=self.to_user, verb='commented', action_object=self.from_user)

    def logout(self):
        self.client.post(reverse('admin:logout') + '?next=/', {})

    def login(self, username, password):
        self.logout()
        response = self.client.post(reverse('login'), {'username': username, 'password': password})
        self.assertEqual(response.status_code, 302)
        return response

    def test_all_messages_page(self):
        self.login('to', 'pwd')
        response = self.client.get(reverse('notifications:all'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notifications']), len(self.to_user.notifications.all()))

    def test_unread_messages_pages(self):
        self.login('to', 'pwd')
        response = self.client.get(reverse('notifications:unread'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notifications']), len(self.to_user.notifications.unread()))
        self.assertEqual(len(response.context['notifications']), self.message_count)

        for index, notification in enumerate(self.to_user.notifications.all()):
            if index % 3 == 0:
                response = self.client.post(reverse('notifications:mark_as_read', args=[id2slug(notification.id)]))
                self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('notifications:unread'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notifications']), len(self.to_user.notifications.unread()))
        self.assertTrue(len(response.context['notifications']) < self.message_count)

        response = self.client.post(reverse('notifications:mark_all_as_read'))
        self.assertRedirects(response, reverse('notifications:unread'))
        response = self.client.get(reverse('notifications:unread'))
        self.assertEqual(len(response.context['notifications']), len(self.to_user.notifications.unread()))
        self.assertEqual(len(response.context['notifications']), 0)

    def test_next_pages(self):
        self.login('to', 'pwd')
        query_parameters = '?var1=hello&var2=world'

        response = self.client.post(
            reverse('notifications:mark_all_as_read'),
            data={
                'next': reverse('notifications:unread') + query_parameters,
            },
        )
        self.assertRedirects(response, reverse('notifications:unread') + query_parameters)

        slug = id2slug(self.to_user.notifications.first().id)
        response = self.client.post(
            reverse('notifications:mark_as_read', args=[slug]),
            data={
                'next': reverse('notifications:unread') + query_parameters,
            },
        )
        self.assertRedirects(response, reverse('notifications:unread') + query_parameters)

        slug = id2slug(self.to_user.notifications.first().id)
        response = self.client.post(
            reverse('notifications:mark_as_unread', args=[slug]),
            {
                'next': reverse('notifications:unread') + query_parameters,
            },
        )
        self.assertRedirects(response, reverse('notifications:unread') + query_parameters)

    @override_settings(ALLOWED_HOSTS=['www.notifications.com'])
    def test_malicious_next_pages(self):
        self.client.force_login(self.to_user)
        query_parameters = '?var1=hello&var2=world'

        for next_url in MALICIOUS_NEXT_URLS:
            response = self.client.post(
                reverse('notifications:mark_all_as_read'),
                data={
                    'next': next_url + query_parameters,
                },
            )
            self.assertRedirects(response, reverse('notifications:unread'))

    def test_state_changing_views_reject_get(self):
        """State-changing views must reject GET with 405 Method Not Allowed."""
        self.login('to', 'pwd')
        slug = id2slug(self.to_user.notifications.first().id)

        for url in [
            reverse('notifications:mark_all_as_read'),
            reverse('notifications:mark_as_read', args=[slug]),
            reverse('notifications:mark_as_unread', args=[slug]),
            reverse('notifications:delete', args=[slug]),
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 405, f'GET {url} should be 405')

    def test_delete_messages_pages(self):
        self.login('to', 'pwd')

        slug = id2slug(self.to_user.notifications.first().id)
        response = self.client.post(reverse('notifications:delete', args=[slug]))
        self.assertRedirects(response, reverse('notifications:all'))

        response = self.client.get(reverse('notifications:all'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notifications']), len(self.to_user.notifications.all()))
        self.assertEqual(len(response.context['notifications']), self.message_count - 1)

        response = self.client.get(reverse('notifications:unread'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notifications']), len(self.to_user.notifications.unread()))
        self.assertEqual(len(response.context['notifications']), self.message_count - 1)

    @override_settings(DJANGO_NOTIFICATIONS_CONFIG={'SOFT_DELETE': True})
    def test_soft_delete_messages_manager(self):
        self.login('to', 'pwd')

        slug = id2slug(self.to_user.notifications.first().id)
        response = self.client.post(reverse('notifications:delete', args=[slug]))
        self.assertRedirects(response, reverse('notifications:all'))

        response = self.client.get(reverse('notifications:all'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notifications']), len(self.to_user.notifications.active()))
        self.assertEqual(len(response.context['notifications']), self.message_count - 1)

        response = self.client.get(reverse('notifications:unread'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notifications']), len(self.to_user.notifications.unread()))
        self.assertEqual(len(response.context['notifications']), self.message_count - 1)

    @override_settings(
        DJANGO_NOTIFICATIONS_CONFIG={
            'SOFT_DELETE': True,
            'USE_JSONFIELD': True,
        }
    )
    def test_soft_delete_api_consistency(self):
        """API count/list endpoints must exclude soft-deleted notifications."""
        self.login('to', 'pwd')

        # Soft-delete one notification
        slug = id2slug(self.to_user.notifications.first().id)
        self.client.post(reverse('notifications:delete', args=[slug]))

        expected_count = self.message_count - 1

        response = self.client.get(reverse('notifications:live_all_notification_count'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['all_count'], expected_count)

        response = self.client.get(reverse('notifications:live_all_notification_list'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['all_count'], expected_count)

    def test_unread_count_api(self):
        self.login('to', 'pwd')

        response = self.client.get(reverse('notifications:live_unread_notification_count'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(list(data.keys()), ['unread_count'])
        self.assertEqual(data['unread_count'], self.message_count)

        Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
        response = self.client.get(reverse('notifications:live_unread_notification_count'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(list(data.keys()), ['unread_count'])
        self.assertEqual(data['unread_count'], 0)

        notify.send(self.from_user, recipient=self.to_user, verb='commented', action_object=self.from_user)
        response = self.client.get(reverse('notifications:live_unread_notification_count'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(list(data.keys()), ['unread_count'])
        self.assertEqual(data['unread_count'], 1)

    def test_all_count_api(self):
        self.login('to', 'pwd')

        response = self.client.get(reverse('notifications:live_all_notification_count'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(list(data.keys()), ['all_count'])
        self.assertEqual(data['all_count'], self.message_count)

        Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
        response = self.client.get(reverse('notifications:live_all_notification_count'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(list(data.keys()), ['all_count'])
        self.assertEqual(data['all_count'], self.message_count)

        notify.send(self.from_user, recipient=self.to_user, verb='commented', action_object=self.from_user)
        response = self.client.get(reverse('notifications:live_all_notification_count'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(list(data.keys()), ['all_count'])
        self.assertEqual(data['all_count'], self.message_count + 1)

    def test_unread_list_api(self):
        self.login('to', 'pwd')

        response = self.client.get(reverse('notifications:live_unread_notification_list'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(sorted(list(data.keys())), ['unread_count', 'unread_list'])
        self.assertEqual(data['unread_count'], self.message_count)
        self.assertEqual(len(data['unread_list']), self.message_count)

        response = self.client.get(reverse('notifications:live_unread_notification_list'), data={'max': 5})
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(sorted(list(data.keys())), ['unread_count', 'unread_list'])
        self.assertEqual(data['unread_count'], self.message_count)
        self.assertEqual(len(data['unread_list']), 5)

        # Test with a bad 'max' value
        response = self.client.get(
            reverse('notifications:live_unread_notification_list'),
            data={
                'max': 'this_is_wrong',
            },
        )
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(sorted(list(data.keys())), ['unread_count', 'unread_list'])
        self.assertEqual(data['unread_count'], self.message_count)
        self.assertEqual(len(data['unread_list']), self.message_count)

        Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
        response = self.client.get(reverse('notifications:live_unread_notification_list'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(sorted(list(data.keys())), ['unread_count', 'unread_list'])
        self.assertEqual(data['unread_count'], 0)
        self.assertEqual(len(data['unread_list']), 0)

        notify.send(self.from_user, recipient=self.to_user, verb='commented', action_object=self.from_user)
        response = self.client.get(reverse('notifications:live_unread_notification_list'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(sorted(list(data.keys())), ['unread_count', 'unread_list'])
        self.assertEqual(data['unread_count'], 1)
        self.assertEqual(len(data['unread_list']), 1)
        self.assertEqual(data['unread_list'][0]['verb'], 'commented')
        self.assertEqual(data['unread_list'][0]['slug'], id2slug(data['unread_list'][0]['id']))

    def test_all_list_api(self):
        self.login('to', 'pwd')

        response = self.client.get(reverse('notifications:live_all_notification_list'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(sorted(list(data.keys())), ['all_count', 'all_list'])
        self.assertEqual(data['all_count'], self.message_count)
        self.assertEqual(len(data['all_list']), self.message_count)

        response = self.client.get(reverse('notifications:live_all_notification_list'), data={'max': 5})
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(sorted(list(data.keys())), ['all_count', 'all_list'])
        self.assertEqual(data['all_count'], self.message_count)
        self.assertEqual(len(data['all_list']), 5)

        # Test with a bad 'max' value
        response = self.client.get(
            reverse('notifications:live_all_notification_list'),
            data={
                'max': 'this_is_wrong',
            },
        )
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(sorted(list(data.keys())), ['all_count', 'all_list'])
        self.assertEqual(data['all_count'], self.message_count)
        self.assertEqual(len(data['all_list']), self.message_count)

        Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
        response = self.client.get(reverse('notifications:live_all_notification_list'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(sorted(list(data.keys())), ['all_count', 'all_list'])
        self.assertEqual(data['all_count'], self.message_count)
        self.assertEqual(len(data['all_list']), self.message_count)

        notify.send(self.from_user, recipient=self.to_user, verb='commented', action_object=self.from_user)
        response = self.client.get(reverse('notifications:live_all_notification_list'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(sorted(list(data.keys())), ['all_count', 'all_list'])
        self.assertEqual(data['all_count'], self.message_count + 1)
        self.assertEqual(len(data['all_list']), self.message_count)
        self.assertEqual(data['all_list'][0]['verb'], 'commented')
        self.assertEqual(data['all_list'][0]['slug'], id2slug(data['all_list'][0]['id']))

    def test_unread_list_api_mark_as_read(self):
        self.login('to', 'pwd')
        num_requested = 3
        response = self.client.get(
            reverse('notifications:live_unread_notification_list'), data={'max': num_requested, 'mark_as_read': 1}
        )
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['unread_count'], self.message_count - num_requested)
        self.assertEqual(len(data['unread_list']), num_requested)
        response = self.client.get(
            reverse('notifications:live_unread_notification_list'), data={'max': num_requested, 'mark_as_read': 1}
        )
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['unread_count'], self.message_count - 2 * num_requested)
        self.assertEqual(len(data['unread_list']), num_requested)

    def test_unread_all_objects(self):
        """
        Test notification with all objects (actor, target, action_object).
        Verifies object URLs are in the output and that get_url_for_notifications
        takes priority over get_absolute_url when both are defined.
        """
        self.login('to', 'pwd')
        Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
        Customer.objects.create(name='to_customer')
        action_customer = Customer.objects.create(name='action_customer')
        from_customer = Customer.objects.create(name='from_customer')
        target_object = TargetObject.objects.create(name='target_object')
        notify.send(
            from_customer, recipient=self.to_user, verb='commented', action_object=action_customer, target=target_object
        )
        response = self.client.get(reverse('notifications:live_unread_notification_list'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['unread_count'], 1)
        notification = data['unread_list'][0]
        self.assertEqual(notification['actor'], 'from_customer')
        self.assertEqual(notification['action_object_url'], f'foo/{action_customer.id}/')
        self.assertEqual(notification['target_url'], f'bar/{target_object.id}/')
        self.assertEqual(notification['actor_url'], f'foo/{from_customer.id}/')

    def test_live_update_tags(self):
        from django.shortcuts import render

        self.login('to', 'pwd')
        factory = RequestFactory()

        request = factory.get('/notification/live_updater')
        request.user = self.to_user

        response = render(
            request, 'notifications/test_tags.html', {'request': request, 'nonce': 'nonce-T5esDNXMnDe5lKMQ6ZzTUw=='}
        )
        content = response.content.decode('utf-8')

        # register_notify_callbacks produces a JSON config block
        self.assertIn('<script type="application/json" id="notify-config"', content)
        self.assertIn('"badgeClass":"live_notify_badge"', content)
        self.assertIn('"apiUrl":', content)
        self.assertIn('"fill_notification_menu"', content)
        self.assertIn('"fill_notification_badge"', content)

        # live_notify_badge renders a span with the unread count
        self.assertIn("<span class='live_notify_badge'>", content)
        self.assertIn(str(self.message_count), content)

        # live_notify_list renders an empty ul
        self.assertIn("<ul class='live_notify_list'></ul>", content)

    def test_anon_user_gets_nothing(self):
        response = self.client.post(reverse('notifications:live_unread_notification_count'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['unread_count'], 0)

        response = self.client.post(reverse('notifications:live_unread_notification_list'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['unread_count'], 0)
        self.assertEqual(data['unread_list'], [])


class NotificationTestExtraData(TestCase):
    """Django notifications automated extra data tests"""

    def setUp(self):
        self.message_count = 1
        self.from_user = User.objects.create_user(username='from', password='pwd', email='example@example.com')
        self.to_user = User.objects.create_user(username='to', password='pwd', email='example@example.com')
        self.to_user.is_staff = True
        self.to_user.save()
        for _ in range(self.message_count):
            notify.send(
                self.from_user,
                recipient=self.to_user,
                verb='commented',
                action_object=self.from_user,
                url='/learn/ask-a-pro/q/test-question-9/299/',
                other_content="Hello my 'world'",
            )

    def logout(self):
        self.client.post(reverse('admin:logout') + '?next=/', {})

    def login(self, username, password):
        self.logout()
        response = self.client.post(reverse('login'), {'username': username, 'password': password})
        self.assertEqual(response.status_code, 302)
        return response

    def test_extra_data(self):
        self.login('to', 'pwd')
        response = self.client.post(reverse('notifications:live_unread_notification_list'))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['unread_list'][0]['data']['url'], '/learn/ask-a-pro/q/test-question-9/299/')
        self.assertEqual(data['unread_list'][0]['data']['other_content'], "Hello my 'world'")


class TagTest(TestCase):
    """Django notifications automated tags tests"""

    def setUp(self):
        self.message_count = 1
        self.from_user = User.objects.create_user(username='from', password='pwd', email='example@example.com')
        self.to_user = User.objects.create_user(username='to', password='pwd', email='example@example.com')
        self.to_user.is_staff = True
        self.to_user.save()
        for _ in range(self.message_count):
            notify.send(
                self.from_user,
                recipient=self.to_user,
                verb='commented',
                action_object=self.from_user,
                url='/learn/ask-a-pro/q/test-question-9/299/',
                other_content="Hello my 'world'",
            )

    def tag_test(self, template, context, output):
        t = Template('{% load notifications_tags %}' + template)
        c = Context(context)
        self.assertEqual(t.render(c), output)

    def test_has_notification(self):
        template = '{{ user|has_notification }}'
        context = {'user': self.to_user}
        output = 'True'
        self.tag_test(template, context, output)

    def test_cached_unread_count_is_per_user(self):
        """Cache key must be scoped per user, not global."""
        from django.core.cache import cache

        from notifications.templatetags.notifications_tags import (
            get_cached_notification_unread_count,
        )

        cache.clear()
        other_user = User.objects.create_user(username='other', password='pwd', email='other@example.com')
        # to_user has 1 notification; other_user has 0
        count_to = get_cached_notification_unread_count(self.to_user)
        count_other = get_cached_notification_unread_count(other_user)
        self.assertEqual(count_to, 1)
        self.assertEqual(count_other, 0)


class NotificationQueryCountTest(TestCase):
    """Verify that listing notifications uses a bounded number of queries."""

    def setUp(self):
        self.message_count = 10
        self.from_user = User.objects.create_user(username='from3', password='pwd', email='example@example.com')
        self.to_user = User.objects.create_user(username='to3', password='pwd', email='example@example.com')
        self.to_user.is_staff = True
        self.to_user.save()
        for _ in range(self.message_count):
            notify.send(self.from_user, recipient=self.to_user, verb='commented', action_object=self.from_user)

    def login(self):
        self.client.login(username='to3', password='pwd')

    def test_all_notifications_view_query_count(self):
        self.login()
        # Warm the ContentType cache
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.clear_cache()
        self.client.get(reverse('notifications:all'))

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('notifications:all'))
            self.assertEqual(response.status_code, 200)
        # session + user + count + paginated qs + prefetches
        # should NOT scale with self.message_count
        self.assertLessEqual(
            len(ctx),
            10,
            f'All-notifications view used {len(ctx)} queries for {self.message_count} '
            f'notifications (expected <= 10, not N+1)',
        )

    def test_unread_list_api_query_count(self):
        self.login()
        # warm caches
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.clear_cache()
        self.client.get(reverse('notifications:live_unread_notification_list'))

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('notifications:live_unread_notification_list'))
            self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(ctx),
            10,
            f'Unread-list API used {len(ctx)} queries for {self.message_count} notifications (expected <= 10, not N+1)',
        )


class AdminTest(TestCase):
    @property
    def app_name(self):
        return Notification._meta.app_label

    def setUp(self):
        self.message_count = 10
        self.from_user = User.objects.create_user(username='from', password='pwd', email='example@example.com')
        self.to_user = User.objects.create_user(username='to', password='pwd', email='example@example.com')
        self.to_user.is_staff = True
        self.to_user.is_superuser = True
        self.to_user.save()
        self.client.login(username='to', password='pwd')
        for _ in range(self.message_count):
            notify.send(
                self.from_user,
                recipient=self.to_user,
                verb='commented',
                action_object=self.from_user,
            )

    def test_list(self):
        with self.assertNumQueries(7):
            response = self.client.get(reverse(f'admin:{self.app_name}_notification_changelist'))
            self.assertEqual(response.status_code, 200, response.content)

    def test_list_display_columns(self):
        """Admin changelist renders the expected columns."""
        response = self.client.get(reverse(f'admin:{self.app_name}_notification_changelist'))
        content = response.content.decode('utf-8')
        for column in ('recipient', 'actor', 'level', 'target', 'unread', 'public'):
            self.assertIn(f'column-{column}', content)

    def test_list_filters(self):
        """Admin changelist exposes the expected filters."""
        response = self.client.get(reverse(f'admin:{self.app_name}_notification_changelist'))
        content = response.content.decode('utf-8')
        for filter_name in ('level', 'unread', 'public', 'timestamp'):
            self.assertIn(f'data-filter-title="{filter_name}"', content)

    def test_mark_unread_action(self):
        """The mark_unread admin action sets selected notifications to unread."""
        # Mark all as read first
        Notification.objects.filter(recipient=self.to_user).update(unread=False)
        self.assertEqual(Notification.objects.filter(recipient=self.to_user, unread=True).count(), 0)

        # Select all and apply the mark_unread action
        notification_ids = list(Notification.objects.filter(recipient=self.to_user).values_list('pk', flat=True))
        self.client.post(
            reverse(f'admin:{self.app_name}_notification_changelist'),
            {
                'action': 'mark_unread',
                '_selected_action': notification_ids,
                'index': '0',
            },
        )
        self.assertEqual(
            Notification.objects.filter(recipient=self.to_user, unread=True).count(),
            self.message_count,
        )


class TemplateTagEscapingTest(TestCase):
    """Escaping sanity checks for template tag XSS vectors."""

    def setUp(self):
        self.from_user = User.objects.create_user(username='from', password='pwd')
        self.to_user = User.objects.create_user(username='to', password='pwd')
        for _ in range(3):
            notify.send(self.from_user, recipient=self.to_user, verb='pinged')

    def test_register_notify_callbacks_escapes_badge_class(self):
        from notifications.templatetags.notifications_tags import register_notify_callbacks

        html = str(register_notify_callbacks(badge_class="'; alert('xss'); //"))
        self.assertIn('application/json', html)
        self.assertNotIn('type="text/javascript"', html)

    def test_register_notify_callbacks_escapes_menu_class(self):
        from notifications.templatetags.notifications_tags import register_notify_callbacks

        html = str(register_notify_callbacks(menu_class='</script><script>alert(1)</script>'))
        self.assertNotIn('</script><script>', html)
        self.assertIn('\\u003C/script\\u003E', html)

    def test_register_notify_callbacks_rejects_invalid_callback(self):
        from notifications.templatetags.notifications_tags import register_notify_callbacks

        with self.assertRaises(ValueError):
            register_notify_callbacks(callbacks="x);document.location='evil';//")

    def test_register_notify_callbacks_accepts_dotted_callback(self):
        from notifications.templatetags.notifications_tags import register_notify_callbacks

        html = str(register_notify_callbacks(callbacks='myApp.handlers.onNotify'))
        self.assertIn('"myApp.handlers.onNotify"', html)

    def test_register_notify_callbacks_escapes_nonce(self):
        from notifications.templatetags.notifications_tags import register_notify_callbacks

        html = str(register_notify_callbacks(nonce='" onload="alert(1)'))
        self.assertIn('nonce="&quot;', html)
        self.assertEqual(html.count('nonce='), 1)

    def test_register_notify_callbacks_output_is_valid_json(self):
        import json as json_mod

        from notifications.templatetags.notifications_tags import register_notify_callbacks

        html = str(
            register_notify_callbacks(
                badge_class='b\'<>&"class',
                callbacks='fill_notification_badge',
                fetch=20,
                mark_as_read=True,
            )
        )
        start = html.index('>') + 1
        end = html.index('</script>')
        config = json_mod.loads(html[start:end])
        self.assertEqual(config['badgeClass'], 'b\'<>&"class')
        self.assertEqual(config['fetchCount'], 20)
        self.assertTrue(config['markAsRead'])
        self.assertEqual(config['callbacks'], ['fill_notification_badge'])

    def test_live_notify_badge_escapes_class(self):
        request = RequestFactory().get('/')
        request.user = self.to_user
        t = Template('{% load notifications_tags %}{% live_notify_badge badge_class=class_name %}')
        html = t.render(
            Context(
                {
                    'request': request,
                    'user': self.to_user,
                    'class_name': "x' onclick='alert(1)'",
                }
            )
        )
        self.assertIn('&#x27;', html)
        self.assertNotIn("onclick='alert", html)

    def test_live_notify_list_escapes_class(self):
        from notifications.templatetags.notifications_tags import live_notify_list

        html = str(live_notify_list(list_class="x'><script>alert(1)</script><ul class='y"))
        self.assertNotIn('<script>', html)
        self.assertIn('&#x27;', html)


class SlugUtilsTest(TestCase):
    """Tests for id2slug / slug2id round-trip conversion."""

    def test_round_trip(self):
        for pk in (1, 42, 999999):
            self.assertEqual(slug2id(id2slug(pk)), pk)

    def test_slug_is_offset(self):
        self.assertEqual(id2slug(0), 110909)
        self.assertEqual(slug2id(110909), 0)

    def test_negative_id_round_trips(self):
        self.assertEqual(slug2id(id2slug(-5)), -5)


class GetNumToFetchTest(TestCase):
    """Tests for helpers.get_num_to_fetch boundary validation."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, **query):
        return self.factory.get('/', query)

    def test_default_when_missing(self):
        self.assertEqual(get_num_to_fetch(self._request()), 10)

    def test_valid_int(self):
        self.assertEqual(get_num_to_fetch(self._request(max='10')), 10)

    def test_max_boundary(self):
        self.assertEqual(get_num_to_fetch(self._request(max='100')), 100)

    def test_over_max_falls_back(self):
        self.assertEqual(get_num_to_fetch(self._request(max='101')), 10)

    def test_zero_falls_back(self):
        self.assertEqual(get_num_to_fetch(self._request(max='0')), 10)

    def test_negative_falls_back(self):
        self.assertEqual(get_num_to_fetch(self._request(max='-1')), 10)

    def test_non_numeric_falls_back(self):
        self.assertEqual(get_num_to_fetch(self._request(max='abc')), 10)


class GetObjectUrlTest(TestCase):
    """Tests for helpers.get_object_url dispatch logic."""

    def setUp(self):
        self.from_user = User.objects.create_user(username='from', password='pwd')
        self.to_user = User.objects.create_user(username='to', password='pwd')
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.request.user = self.to_user
        notify.send(self.from_user, recipient=self.to_user, verb='tested')
        self.notification = Notification.objects.get(recipient=self.to_user)

    def test_get_url_for_notifications_takes_priority(self):
        target = TargetObject.objects.create(name='t')
        url = get_object_url(target, self.notification, self.request)
        self.assertEqual(url, f'bar/{target.id}/')

    def test_falls_back_to_get_absolute_url(self):
        customer = Customer.objects.create(name='c')
        url = get_object_url(customer, self.notification, self.request)
        self.assertEqual(url, f'foo/{customer.id}/')

    def test_returns_none_when_no_url_method(self):
        url = get_object_url(self.from_user, self.notification, self.request)
        self.assertIsNone(url)


class NotificationInstanceMethodTest(TestCase):
    """Tests for Notification model instance methods."""

    def setUp(self):
        self.from_user = User.objects.create_user(username='from', password='pwd')
        self.to_user = User.objects.create_user(username='to', password='pwd')
        notify.send(self.from_user, recipient=self.to_user, verb='commented', action_object=self.from_user)
        self.notification = Notification.objects.get(recipient=self.to_user)

    def test_slug_property(self):
        self.assertEqual(self.notification.slug, id2slug(self.notification.id))

    def test_mark_as_read_idempotent(self):
        self.assertTrue(self.notification.unread)
        self.notification.mark_as_read()
        self.assertFalse(self.notification.unread)
        self.notification.mark_as_read()
        self.assertFalse(self.notification.unread)

    def test_mark_as_unread_idempotent(self):
        self.notification.mark_as_read()
        self.assertFalse(self.notification.unread)
        self.notification.mark_as_unread()
        self.assertTrue(self.notification.unread)
        self.notification.mark_as_unread()
        self.assertTrue(self.notification.unread)

    def test_str_with_action_object_and_target(self):
        target = Customer.objects.create(name='target_obj')
        notify.send(self.from_user, recipient=self.to_user, verb='edited', action_object=self.from_user, target=target)
        n = Notification.objects.filter(recipient=self.to_user, verb='edited').first()
        text = str(n)
        self.assertIn('edited', text)
        self.assertIn('target_obj', text)

    def test_str_with_target_only(self):
        target = Customer.objects.create(name='tgt')
        notify.send(self.from_user, recipient=self.to_user, verb='viewed', target=target)
        n = Notification.objects.filter(recipient=self.to_user, verb='viewed').first()
        text = str(n)
        self.assertIn('viewed', text)
        self.assertIn('tgt', text)
        self.assertNotIn('None', text)

    def test_str_verb_only(self):
        notify.send(self.from_user, recipient=self.to_user, verb='logged in')
        n = Notification.objects.filter(recipient=self.to_user, verb='logged in').first()
        text = str(n)
        self.assertIn('logged in', text)

    def test_actor_object_url_returns_admin_link(self):
        html = self.notification.actor_object_url()
        self.assertIn(str(self.notification.actor_object_id), html)

    def test_action_object_url_returns_admin_link(self):
        html = self.notification.action_object_url()
        self.assertIn(str(self.notification.action_object_object_id), html)


class SentUnsentQuerySetTest(TestCase):
    """Tests for sent/unsent queryset methods."""

    def setUp(self):
        self.from_user = User.objects.create_user(username='from', password='pwd')
        self.to_user = User.objects.create_user(username='to', password='pwd')
        for _ in range(5):
            notify.send(self.from_user, recipient=self.to_user, verb='pinged')

    def test_all_start_unsent(self):
        self.assertEqual(Notification.objects.unsent().count(), 5)
        self.assertEqual(Notification.objects.sent().count(), 0)

    def test_mark_as_sent(self):
        Notification.objects.mark_as_sent()
        self.assertEqual(Notification.objects.sent().count(), 5)
        self.assertEqual(Notification.objects.unsent().count(), 0)

    def test_mark_as_unsent(self):
        Notification.objects.mark_as_sent()
        Notification.objects.mark_as_unsent()
        self.assertEqual(Notification.objects.unsent().count(), 5)


class UnreadCountCacheInvalidationTest(TestCase):
    """Mutating views must drop the cached unread count.

    Without this the ``{% notifications_unread %}`` badge keeps showing
    the old number for up to ``CACHE_TIMEOUT`` seconds after the user
    marks something read or deletes it.
    """

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.from_user = User.objects.create_user(username='from', password='pwd')
        self.to_user = User.objects.create_user(username='to', password='pwd')
        for _ in range(3):
            notify.send(self.from_user, recipient=self.to_user, verb='pinged')
        self.client.force_login(self.to_user)

    def _seed_cache(self, value=3):
        from django.core.cache import cache

        from notifications.templatetags.notifications_tags import unread_count_cache_key

        cache.set(unread_count_cache_key(self.to_user), value, 60)

    def _cache_key(self):
        from notifications.templatetags.notifications_tags import unread_count_cache_key

        return unread_count_cache_key(self.to_user)

    def test_mark_as_read_drops_cache(self):
        from django.core.cache import cache

        self._seed_cache()
        n = self.to_user.notifications.first()
        self.client.post(reverse('notifications:mark_as_read', kwargs={'slug': n.slug}))
        self.assertIsNone(cache.get(self._cache_key()))

    def test_mark_as_unread_drops_cache(self):
        from django.core.cache import cache

        n = self.to_user.notifications.first()
        n.mark_as_read()
        self._seed_cache(value=2)
        self.client.post(reverse('notifications:mark_as_unread', kwargs={'slug': n.slug}))
        self.assertIsNone(cache.get(self._cache_key()))

    def test_mark_all_as_read_drops_cache(self):
        from django.core.cache import cache

        self._seed_cache()
        self.client.post(reverse('notifications:mark_all_as_read'))
        self.assertIsNone(cache.get(self._cache_key()))

    def test_delete_drops_cache(self):
        from django.core.cache import cache

        self._seed_cache()
        n = self.to_user.notifications.first()
        self.client.post(reverse('notifications:delete', kwargs={'slug': n.slug}))
        self.assertIsNone(cache.get(self._cache_key()))

    def test_live_unread_list_with_mark_as_read_drops_cache(self):
        """``?mark_as_read=true`` on the live JSON list also bulk-marks rows."""
        from django.core.cache import cache

        self._seed_cache()
        self.client.get(reverse('notifications:live_unread_notification_list') + '?mark_as_read=true')
        self.assertIsNone(cache.get(self._cache_key()))

    def test_live_unread_list_without_mark_as_read_keeps_cache(self):
        """A plain GET should not invalidate the cache."""
        from django.core.cache import cache

        self._seed_cache(value=42)
        self.client.get(reverse('notifications:live_unread_notification_list'))
        self.assertEqual(cache.get(self._cache_key()), 42)
