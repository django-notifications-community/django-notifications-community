import json
import os
from unittest import skipUnless

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from notifications.signals import notify
from notifications.swappable import load_notification_model
from notifications.tests.tests import AdminTest as BaseAdminTest
from notifications.tests.tests import NotificationTest as BaseNotificationTest

Notification = load_notification_model()


@skipUnless(os.environ.get('SAMPLE_APP', False), 'Running tests on standard django-notifications models')
class AdminTest(BaseAdminTest):
    pass


@skipUnless(os.environ.get('SAMPLE_APP', False), 'Running tests on standard django-notifications models')
class NotificationTest(BaseNotificationTest):
    pass


class TestExtraDataCustomAccessor(NotificationTest):
    def setUp(self):
        self.from_user = User.objects.create_user(username='from_extra', password='pwd', email='example@example.com')
        self.to_user = User.objects.create_user(username='to_extra', password='pwd', email='example@example.com')
        notify.send(
            self.from_user,
            recipient=self.to_user,
            verb='commented',
            action_object=self.from_user,
            url='/learn/ask-a-pro/q/test-question-9/299/',
            other_content="Hello my 'world'",
            details='test detail',
        )

    def test_extra_data(self):
        notification = Notification.objects.get(details='test detail')
        assert notification, 'Expected a notification retrieved by custom extra data accessor'
        assert notification.details == 'test detail', 'Custom accessor should return set value'
        assert 'details' not in notification.data, 'Custom accessor should not be in json data'


@skipUnless(os.environ.get('SAMPLE_APP', False), 'Running tests on standard django-notifications models')
class TestMultiRecipientKwargs(TestCase):
    """Regression test for issue #3: kwargs lost for all recipients after the first."""

    def setUp(self):
        self.from_user = User.objects.create_user(username='from_multi', password='pwd', email='a@example.com')
        self.to_user_1 = User.objects.create_user(username='to_multi_1', password='pwd', email='b@example.com')
        self.to_user_2 = User.objects.create_user(username='to_multi_2', password='pwd', email='c@example.com')
        notify.send(
            self.from_user,
            recipient=[self.to_user_1, self.to_user_2],
            verb='commented',
            action_object=self.from_user,
            details='shared detail',
            extra_key='extra_value',
        )

    def test_all_recipients_get_custom_field(self):
        for user in [self.to_user_1, self.to_user_2]:
            notification = Notification.objects.get(recipient=user)
            self.assertEqual(
                notification.details,
                'shared detail',
                f"Recipient {user.username} should have details='shared detail', got '{notification.details}'",
            )

    def test_all_recipients_get_data_kwargs(self):
        for user in [self.to_user_1, self.to_user_2]:
            notification = Notification.objects.get(recipient=user)
            self.assertIn('extra_key', notification.data)
            self.assertEqual(notification.data['extra_key'], 'extra_value')


@skipUnless(os.environ.get('SAMPLE_APP', False), 'Running tests on standard django-notifications models')
class TestSwappedModelFieldsInApi(TestCase):
    """Regression test for issue #73: fields added to a swapped model must
    show up in the json endpoints.

    The models module is imported per test rather than at module level:
    without SAMPLE_APP the app is out of INSTALLED_APPS, and importing it
    anyway registers a second Notification model that trips the system
    checks for the whole suite.
    """

    def setUp(self):
        self.from_user = User.objects.create_user(username='from_api', password='pwd', email='a@example.com')
        self.to_user = User.objects.create_user(username='to_api', password='pwd', email='b@example.com')
        notify.send(
            self.from_user,
            recipient=self.to_user,
            verb='commented',
            action_object=self.from_user,
            details='custom field value',
        )
        self.client.login(username='to_api', password='pwd')

    def test_custom_field_in_all_list(self):
        response = self.client.get(reverse('notifications:live_all_notification_list'))
        struct = json.loads(response.content.decode('utf-8'))['all_list'][0]
        self.assertIn('details', struct)
        self.assertEqual(struct['details'], 'custom field value')

    def test_custom_field_in_unread_list(self):
        response = self.client.get(reverse('notifications:live_unread_notification_list'))
        struct = json.loads(response.content.decode('utf-8'))['unread_list'][0]
        self.assertIn('details', struct)
        self.assertEqual(struct['details'], 'custom field value')

    def test_plumbing_fields_stay_out(self):
        response = self.client.get(reverse('notifications:live_all_notification_list'))
        struct = json.loads(response.content.decode('utf-8'))['all_list'][0]
        for field in ['recipient', 'actor_content_type', 'actor_object_id']:
            self.assertNotIn(field, struct)

    def test_m2m_field_does_not_break_the_endpoint(self):
        """A m2m value is a list of model instances, which JsonResponse cannot encode."""
        from notifications.tests.sample_notifications.models import Tag

        notification = Notification.objects.get(recipient=self.to_user)
        notification.tags.add(Tag.objects.create(name='urgent'))

        response = self.client.get(reverse('notifications:live_all_notification_list'))

        self.assertEqual(response.status_code, 200)
        struct = json.loads(response.content.decode('utf-8'))['all_list'][0]
        self.assertNotIn('tags', struct)

    def test_m2m_field_costs_no_extra_query(self):
        from notifications.tests.sample_notifications.models import Tag

        notification = Notification.objects.get(recipient=self.to_user)
        notification.tags.add(Tag.objects.create(name='urgent'))
        url = reverse('notifications:live_all_notification_list')
        self.client.get(url)  # warm the content type cache

        with CaptureQueriesContext(connection) as queries:
            self.client.get(url)
        tag_queries = [q for q in queries.captured_queries if 'sample_notifications_tag' in q['sql']]

        self.assertEqual(tag_queries, [])

    @override_settings(DJANGO_NOTIFICATIONS_CONFIG={'USE_JSONFIELD': True, 'API_EXCLUDED_FIELDS': ['details']})
    def test_api_excluded_fields_holds_back_a_custom_field(self):
        response = self.client.get(reverse('notifications:live_all_notification_list'))
        struct = json.loads(response.content.decode('utf-8'))['all_list'][0]
        self.assertNotIn('details', struct)
        self.assertIn('verb', struct)

    def test_file_field_is_serialized_as_its_path(self):
        notification = Notification.objects.get(recipient=self.to_user)
        notification.attachment = 'attachments/report.pdf'
        notification.save(update_fields=['attachment'])

        response = self.client.get(reverse('notifications:live_all_notification_list'))

        self.assertEqual(response.status_code, 200)
        struct = json.loads(response.content.decode('utf-8'))['all_list'][0]
        self.assertEqual(struct['attachment'], 'attachments/report.pdf')
