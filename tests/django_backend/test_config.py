import os
import sys
from pathlib import Path
import pytest

# Ensure django_backend is in sys.path for test discovery
django_dir = Path(__file__).resolve().parent.parent.parent / "django_backend"
if str(django_dir) not in sys.path:
    sys.path.insert(0, str(django_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

def test_django_settings_loaded():
    """Verify Django configuration settings load cleanly without errors."""
    import django
    django.setup()
    from django.conf import settings
    assert settings.SECRET_KEY is not None
    assert "apps.accounts" in settings.INSTALLED_APPS
    assert "apps.incidents" in settings.INSTALLED_APPS

def test_django_health_endpoint():
    """Verify Django control plane health check view returns 200 OK."""
    import django
    django.setup()
    from django.test import Client
    client = Client()
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "django_control_plane"
