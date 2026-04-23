from notifications.apps import Config as NotificationConfig


class SampleNotificationsConfig(NotificationConfig):
    name = 'notifications.tests.sample_notifications'
    label = 'sample_notifications'
    # Disambiguates auto-discovery: the import alias above puts the
    # base Config in the module namespace, so Django sees two AppConfig
    # candidates and needs one explicitly marked as the default.
    default = True
