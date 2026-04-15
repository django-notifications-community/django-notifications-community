import os
from unittest import skipUnless

from django.contrib.auth.models import User
from django.test import TestCase

from notifications.signals import notify
from notifications.swappable import load_notification_model
from notifications.tests.tests import AdminTest as BaseAdminTest
from notifications.tests.tests import NotificationTest as BaseNotificationTest

Notification = load_notification_model()


@skipUnless(os.environ.get('SAMPLE_APP', False), 'Running tests on standard django-notifications models')
class AdminTest(BaseAdminTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        BaseAdminTest.app_name = 'sample_notifications'


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
