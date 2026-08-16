"""
Test settings for Django - uses SQLite for fast testing.
"""

from .settings import *  # noqa: F403
from .settings import SIMPLE_JWT

# Override database for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Use faster password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable CORS for tests
CORS_ALLOW_ALL_ORIGINS = True

# Disable token blacklisting for tests (requires migrations)
SIMPLE_JWT = {
    **SIMPLE_JWT,
    "BLACKLIST_AFTER_ROTATION": False,
    "ROTATE_REFRESH_TOKENS": False,
}
