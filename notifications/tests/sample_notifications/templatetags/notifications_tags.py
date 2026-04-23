# Re-export the tag library so it stays available when SAMPLE_APP=1
# removes the main ``notifications`` app from INSTALLED_APPS.
from notifications.templatetags.notifications_tags import *  # noqa: F401, F403
from notifications.templatetags.notifications_tags import register  # noqa: F401
