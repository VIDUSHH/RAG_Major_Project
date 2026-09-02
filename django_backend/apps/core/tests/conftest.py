"""Test configuration for core app tests."""

import django
from django.conf import settings

# Ensure Django is configured
if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "rest_framework",
            "rest_framework_simplejwt",
            "apps.accounts",
            "apps.organizations",
            "apps.core",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        SECRET_KEY="test-secret-key",
        AUTH_USER_MODEL="accounts.User",
        REST_FRAMEWORK={
            "DEFAULT_AUTHENTICATION_CLASSES": [
                "rest_framework_simplejwt.authentication.JWTAuthentication",
            ],
        },
    )
    django.setup()
