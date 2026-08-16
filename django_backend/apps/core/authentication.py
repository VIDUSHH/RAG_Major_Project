from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import exceptions

from apps.api_keys.models import APIKey

_API_KEY_PREFIX = "ApiKey "


class APIKeyAuthentication:
    """
    Custom authentication backend that reads X-API-Key header.
    Hashes the incoming key and looks it up in APIKey table.
    Checks scope, expiry, active status.
    """

    def authenticate(self, request):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith(_API_KEY_PREFIX):
                api_key = auth_header[len(_API_KEY_PREFIX) :]
            else:
                return None  # Bearer or other schemes fall through to the next backend

        if not api_key:
            return None

        key_hash = APIKey.hash_key(api_key)
        prefix = api_key[:8]

        try:
            api_key_obj = APIKey.objects.select_related("organization", "created_by").get(
                key_hash=key_hash, prefix=prefix
            )
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key") from None

        if not api_key_obj.is_active:
            raise exceptions.AuthenticationFailed("API key is disabled") from None

        if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now():
            raise exceptions.AuthenticationFailed("API key has expired") from None

        # Update last_used_at
        api_key_obj.last_used_at = timezone.now()
        api_key_obj.save(update_fields=["last_used_at"])

        # Return user (created_by) or None for service accounts
        user = api_key_obj.created_by
        if user and not user.is_active:
            raise exceptions.AuthenticationFailed("User account is disabled")

        return (user, api_key_obj)

    def authenticate_header(self, request):
        return "ApiKey"


class InternalAPIKeyAuthentication:
    """
    Authentication for service-to-service calls (Django -> FastAPI).
    Validates X-Internal-API-Key header against FASTAPI_INTERNAL_API_KEY.
    """

    def __init__(self):
        from django.conf import settings

        self.expected_key = getattr(settings, "FASTAPI_INTERNAL_API_KEY", None)

    def authenticate(self, request):
        internal_key = request.headers.get("X-Internal-API-Key")

        if not internal_key:
            return None

        if not self.expected_key:
            raise exceptions.AuthenticationFailed("Internal API key not configured")

        if internal_key != self.expected_key:
            raise exceptions.AuthenticationFailed("Invalid internal API key")

        # Return a synthetic user for internal calls
        user_model = get_user_model()
        internal_user, _ = user_model.objects.get_or_create(
            email="internal@system.local",
            defaults={
                "full_name": "Internal System",
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        return (internal_user, None)

    def authenticate_header(self, request):
        return "InternalApiKey"
