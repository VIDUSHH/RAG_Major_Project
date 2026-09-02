import pytest
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.models import User
from apps.api_keys.models import APIKey
from apps.core.authentication import APIKeyAuthentication, InternalAPIKeyAuthentication
from apps.organizations.models import Organization


@pytest.fixture
def api_key_obj(db):
    org = Organization.objects.create(name="Test Org", slug="test-org")
    user = User.objects.create_user(email="test@example.com", password="testpass123")
    plain_key, key_hash, prefix = APIKey.generate_key()
    api_key = APIKey.objects.create(
        organization=org,
        name="Test API Key",
        key_hash=key_hash,
        prefix=prefix,
        scopes=["read:incidents", "write:postmortems"],
        created_by=user,
    )
    return api_key, plain_key, user


class TestAPIKeyAuthentication:
    @pytest.mark.django_db
    def test_authenticate_valid_key(self, api_key_obj, rf):
        api_key, plain_key, user = api_key_obj
        request = rf.get("/api/test", HTTP_X_API_KEY=plain_key)
        request._request = request

        auth = APIKeyAuthentication()
        result = auth.authenticate(request)

        assert result is not None
        assert result[0] == user
        assert result[1] == api_key

    @pytest.mark.django_db
    def test_authenticate_invalid_key(self, rf):
        request = rf.get("/api/test", HTTP_X_API_KEY="invalid_key")
        request._request = request

        auth = APIKeyAuthentication()
        with pytest.raises(AuthenticationFailed, match="Invalid API key"):
            auth.authenticate(request)

    @pytest.mark.django_db
    def test_authenticate_missing_key(self, rf):
        request = rf.get("/api/test")
        request._request = request

        auth = APIKeyAuthentication()
        result = auth.authenticate(request)

        assert result is None

    @pytest.mark.django_db
    def test_authenticate_disabled_key(self, api_key_obj, rf):
        api_key, plain_key, user = api_key_obj
        api_key.is_active = False
        api_key.save()

        request = rf.get("/api/test", HTTP_X_API_KEY=plain_key)
        request._request = request

        auth = APIKeyAuthentication()
        with pytest.raises(AuthenticationFailed, match="API key is disabled"):
            auth.authenticate(request)

    @pytest.mark.django_db
    def test_authenticate_expired_key(self, api_key_obj, rf):
        from datetime import timedelta

        from django.utils import timezone

        api_key, plain_key, user = api_key_obj
        api_key.expires_at = timezone.now() - timedelta(days=1)
        api_key.save()

        request = rf.get("/api/test", HTTP_X_API_KEY=plain_key)
        request._request = request

        auth = APIKeyAuthentication()
        with pytest.raises(AuthenticationFailed, match="API key has expired"):
            auth.authenticate(request)

    @pytest.mark.django_db
    def test_authenticate_updates_last_used(self, api_key_obj, rf):

        api_key, plain_key, user = api_key_obj
        old_last_used = api_key.last_used_at

        request = rf.get("/api/test", HTTP_X_API_KEY=plain_key)
        request._request = request

        auth = APIKeyAuthentication()
        auth.authenticate(request)

        api_key.refresh_from_db()
        assert api_key.last_used_at is not None
        if old_last_used:
            assert api_key.last_used_at > old_last_used

    @pytest.mark.django_db
    def test_authenticate_inactive_user(self, api_key_obj, rf):
        api_key, plain_key, user = api_key_obj
        user.is_active = False
        user.save()

        request = rf.get("/api/test", HTTP_X_API_KEY=plain_key)
        request._request = request

        auth = APIKeyAuthentication()
        with pytest.raises(AuthenticationFailed, match="User account is disabled"):
            auth.authenticate(request)


class TestInternalAPIKeyAuthentication:
    @pytest.mark.django_db
    def test_authenticate_valid_key(self, rf, settings):
        settings.FASTAPI_INTERNAL_API_KEY = "test-internal-key"

        request = rf.post("/internal/test", HTTP_X_INTERNAL_API_KEY="test-internal-key")
        request._request = request

        auth = InternalAPIKeyAuthentication()
        result = auth.authenticate(request)

        assert result is not None
        assert result[0].email == "internal@system.local"
        assert result[0].is_staff is True

    @pytest.mark.django_db
    def test_authenticate_invalid_key(self, rf, settings):
        settings.FASTAPI_INTERNAL_API_KEY = "test-internal-key"

        request = rf.post("/internal/test", HTTP_X_INTERNAL_API_KEY="wrong-key")
        request._request = request

        auth = InternalAPIKeyAuthentication()
        with pytest.raises(AuthenticationFailed, match="Invalid internal API key"):
            auth.authenticate(request)

    @pytest.mark.django_db
    def test_authenticate_missing_key(self, rf, settings):
        settings.FASTAPI_INTERNAL_API_KEY = "test-internal-key"

        request = rf.post("/internal/test")
        request._request = request

        auth = InternalAPIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None

    @pytest.mark.django_db
    def test_authenticate_not_configured(self, rf, settings):
        # Don't set the key
        if hasattr(settings, "FASTAPI_INTERNAL_API_KEY"):
            delattr(settings, "FASTAPI_INTERNAL_API_KEY")

        request = rf.post("/internal/test", HTTP_X_INTERNAL_API_KEY="test-key")
        request._request = request

        auth = InternalAPIKeyAuthentication()
        with pytest.raises(AuthenticationFailed, match="Internal API key not configured"):
            auth.authenticate(request)
