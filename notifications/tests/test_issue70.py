"""Regression tests for issue #70.

notify.send() silently accepted non-instance values (a model class, or an
unsaved instance with pk=None) for sender / target / action_object, then
wrote nonsense into the CharField object_id columns. The resulting rows
crashed any view that did prefetch_related('actor', ...) with
``ValueError: Field 'id' expected a number``.

These tests pin the desired behavior: notify.send must refuse the bad
input up front and persist nothing.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from notifications.signals import notify
from notifications.swappable import load_notification_model
from notifications.tests.test_models.models import Customer

Notification = load_notification_model()


class NotifySendRejectsModelClassesTest(TestCase):
    def setUp(self):
        self.recipient = User.objects.create_user(
            username='inboxuser', password='pwd', email='inbox@example.com'
        )
        self.actor = User.objects.create_user(
            username='actor', password='pwd', email='actor@example.com'
        )
        self.customer = Customer.objects.create(name='c', address='x')

    def test_sender_as_class_raises(self):
        with self.assertRaises(TypeError) as cm:
            notify.send(User, recipient=self.recipient, verb='you reached level 10')
        self.assertIn('sender', str(cm.exception).lower())

    def test_target_as_class_raises(self):
        with self.assertRaises(TypeError) as cm:
            notify.send(
                self.actor,
                recipient=self.recipient,
                verb='commented',
                target=Customer,
            )
        self.assertIn('target', str(cm.exception).lower())

    def test_action_object_as_class_raises(self):
        with self.assertRaises(TypeError) as cm:
            notify.send(
                self.actor,
                recipient=self.recipient,
                verb='commented',
                action_object=Customer,
            )
        self.assertIn('action_object', str(cm.exception).lower())

    def test_no_notification_persisted_when_sender_is_class(self):
        with self.assertRaises(TypeError):
            notify.send(User, recipient=self.recipient, verb='you reached level 10')
        self.assertEqual(Notification.objects.count(), 0)

    def test_no_notification_persisted_when_target_is_class(self):
        with self.assertRaises(TypeError):
            notify.send(
                self.actor,
                recipient=self.recipient,
                verb='commented',
                target=Customer,
            )
        self.assertEqual(Notification.objects.count(), 0)


class NotifySendRejectsUnsavedInstancesTest(TestCase):
    def setUp(self):
        self.recipient = User.objects.create_user(
            username='inboxuser', password='pwd', email='inbox@example.com'
        )
        self.actor = User.objects.create_user(
            username='actor', password='pwd', email='actor@example.com'
        )

    def test_unsaved_sender_raises(self):
        # Django's Signal.send() hashes the sender for the dispatch cache and
        # rejects unsaved instances with TypeError before our handler runs.
        # Our own ValueError would only fire if Django ever changes that.
        unsaved = User(username='ghost', email='g@example.com')
        with self.assertRaises((TypeError, ValueError)):
            notify.send(unsaved, recipient=self.recipient, verb='commented')

    def test_unsaved_target_raises(self):
        unsaved = Customer(name='ghost', address='nowhere')
        with self.assertRaises(ValueError) as cm:
            notify.send(
                self.actor,
                recipient=self.recipient,
                verb='commented',
                target=unsaved,
            )
        self.assertIn('target', str(cm.exception).lower())

    def test_unsaved_action_object_raises(self):
        unsaved = Customer(name='ghost', address='nowhere')
        with self.assertRaises(ValueError) as cm:
            notify.send(
                self.actor,
                recipient=self.recipient,
                verb='commented',
                action_object=unsaved,
            )
        self.assertIn('action_object', str(cm.exception).lower())

    def test_no_notification_persisted_when_sender_unsaved(self):
        unsaved = User(username='ghost', email='g@example.com')
        with self.assertRaises((TypeError, ValueError)):
            notify.send(unsaved, recipient=self.recipient, verb='commented')
        self.assertEqual(Notification.objects.count(), 0)


class NotifySendStillAcceptsValidInputTest(TestCase):
    """Sanity check that the new validation doesn't break the happy path."""

    def setUp(self):
        self.recipient = User.objects.create_user(
            username='inboxuser', password='pwd', email='inbox@example.com'
        )
        self.actor = User.objects.create_user(
            username='actor', password='pwd', email='actor@example.com'
        )
        self.customer = Customer.objects.create(name='c', address='x')

    def test_saved_instances_round_trip(self):
        notify.send(
            self.actor,
            recipient=self.recipient,
            verb='commented',
            target=self.customer,
            action_object=self.customer,
        )
        n = Notification.objects.get(recipient=self.recipient)
        self.assertEqual(n.actor_object_id, str(self.actor.pk))
        self.assertEqual(n.target_object_id, str(self.customer.pk))
        self.assertEqual(n.action_object_object_id, str(self.customer.pk))

    def test_inbox_view_renders_after_valid_send(self):
        notify.send(self.actor, recipient=self.recipient, verb='commented')
        self.client.force_login(self.recipient)
        response = self.client.get(reverse('notifications:all'))
        self.assertEqual(response.status_code, 200)
