"""Django notification urls for tests"""

from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path

from notifications.tests.views import (
    live_tester,
    make_notification,
)

urlpatterns = [
    path('test_make/', make_notification),
    path('test/', live_tester),
    path('login/', LoginView.as_view(), name='login'),
    path('admin/', admin.site.urls),
    path('', include('notifications.urls', namespace='notifications')),
]
