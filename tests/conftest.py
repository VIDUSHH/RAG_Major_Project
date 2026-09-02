"""
Root conftest.py — configures pytest-django and shared fixtures.

pytest.ini sets pythonpath = fastapi_backend django_backend so both
packages resolve cleanly without any sys.path manipulation in test files.
"""

import pytest

# Tell pytest-django which settings module to use.
# This replaces the inline os.environ.setdefault calls that were in each test file.
django_settings = pytest.ini_options = {}


def pytest_configure(config):
    """Set Django settings module before any test collection."""
    from django.conf import settings as django_settings_obj

    if not django_settings_obj.configured:
        import os

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
