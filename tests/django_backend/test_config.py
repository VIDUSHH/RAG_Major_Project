def test_django_settings_loaded():
    """Verify Django configuration settings load cleanly without errors."""
    import django

    django.setup()
    from django.conf import settings

    assert settings.SECRET_KEY is not None
    assert "apps.accounts" in settings.INSTALLED_APPS
    assert "apps.incidents" in settings.INSTALLED_APPS
    assert "apps.log_sources" in settings.INSTALLED_APPS
    assert "rest_framework" in settings.INSTALLED_APPS


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
