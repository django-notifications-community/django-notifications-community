# -*- coding: utf-8 -*-
"""
    django-notifications
    ~~~~~
    A GitHub notification alike app for Django.
    :copyright: (c) 2015 by django-notifications team.
    :copyright: (c) 2026 by django-notifications-community contributors.
    :license: BSD, see LICENSE.txt for more details.
"""
from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("django-notifications-community")
except PackageNotFoundError:
    # Running from a source checkout without `pip install -e .`.
    __version__ = "0.0.0+unknown"

default_app_config = 'notifications.apps.Config'  # pylint: disable=invalid-name
