"""
Django control-plane failure-path and negative tests.

Tests what happens when:
- An unknown URL is requested (404)
- Django settings are missing critical keys
- Forbidden configuration states are detected
"""


def test_unknown_url_returns_404():
    """Unknown routes should return 404, not 500."""
    import django

    django.setup()
    from django.test import Client

    client = Client()
    response = client.get("/api/nonexistent-route/")
    assert response.status_code == 404


def test_settings_has_no_sqlite_database():
    """
    PostgreSQL must be the only configured database.
    The engine must never be sqlite3 — that would indicate the SQLite
    fallback has been reintroduced.
    """
    import importlib

    import config.settings as s

    # Re-evaluate the main settings module without test overrides
    importlib.reload(s)

    db_engine = s.DATABASES["default"]["ENGINE"]
    assert "sqlite" not in db_engine, (
        f"SQLite must not be used as the database engine. Got: {db_engine}"
    )
    assert "postgresql" in db_engine, f"PostgreSQL engine expected. Got: {db_engine}"


def test_settings_debug_flag_is_boolean():
    """DEBUG must be a boolean, not a string."""
    import django

    django.setup()
    from django.conf import settings

    assert isinstance(settings.DEBUG, bool)


def test_cors_allow_all_origins_off_in_production():
    """
    When CORS_ALLOWED_ORIGINS env var is set, CORS_ALLOW_ALL_ORIGINS
    must be False regardless of DEBUG state.
    """
    import importlib
    import os

    original = os.environ.get("CORS_ALLOWED_ORIGINS")
    try:
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://app.example.com"
        # Re-evaluate the settings value in a fresh import
        import config.settings as s

        importlib.reload(s)
        assert not getattr(s, "CORS_ALLOW_ALL_ORIGINS", True), (
            "CORS_ALLOW_ALL_ORIGINS must be False when CORS_ALLOWED_ORIGINS is explicitly set"
        )
        assert "https://app.example.com" in getattr(s, "CORS_ALLOWED_ORIGINS", [])
    finally:
        if original is None:
            os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        else:
            os.environ["CORS_ALLOWED_ORIGINS"] = original
