import pytest

from apps.accounts.models import User
from apps.api_keys.models import APIKey
from apps.organizations.models import Organization


@pytest.mark.django_db
class TestAPIKeyModel:
    def test_api_key_creation(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        plain_key, key_hash, prefix = APIKey.generate_key()
        api_key = APIKey.objects.create(
            organization=org,
            name="Test API Key",
            key_hash=key_hash,
            prefix=prefix,
            scopes=["read:incidents", "write:postmortems"],
        )
        assert api_key.name == "Test API Key"
        assert api_key.key_hash == key_hash
        assert api_key.prefix == prefix
        assert api_key.scopes == ["read:incidents", "write:postmortems"]
        assert api_key.is_active is True
        assert api_key.id is not None

    def test_api_key_str(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        plain_key, key_hash, prefix = APIKey.generate_key()
        api_key = APIKey.objects.create(
            organization=org,
            name="Test API Key",
            key_hash=key_hash,
            prefix=prefix,
        )
        assert str(api_key) == f"Test Org / Test API Key ({prefix}...)"

    def test_generate_key(self):
        plain_key, key_hash, prefix = APIKey.generate_key()
        assert plain_key.startswith("sk_")
        assert len(key_hash) == 64
        assert len(prefix) == 8

    def test_hash_key(self):
        plain_key = "sk_testkey123"
        key_hash = APIKey.hash_key(plain_key)
        assert len(key_hash) == 64
        assert key_hash == APIKey.hash_key(plain_key)

    def test_verify_key(self):
        plain_key, key_hash, prefix = APIKey.generate_key()
        api_key = APIKey(
            organization=Organization.objects.create(name="Test Org", slug="test-org"),
            name="Test API Key",
            key_hash=key_hash,
            prefix=prefix,
        )
        assert api_key.verify_key(plain_key) is True
        assert api_key.verify_key("wrong_key") is False

    def test_scopes_json_field(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        plain_key, key_hash, prefix = APIKey.generate_key()
        api_key = APIKey.objects.create(
            organization=org,
            name="Test API Key",
            key_hash=key_hash,
            prefix=prefix,
            scopes=["read:incidents", "write:postmortems", "admin:organizations"],
        )
        assert api_key.scopes == ["read:incidents", "write:postmortems", "admin:organizations"]

    def test_default_scopes(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        plain_key, key_hash, prefix = APIKey.generate_key()
        api_key = APIKey.objects.create(
            organization=org,
            name="Test API Key",
            key_hash=key_hash,
            prefix=prefix,
        )
        assert api_key.scopes == []

    def test_is_active_default(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        plain_key, key_hash, prefix = APIKey.generate_key()
        api_key = APIKey.objects.create(
            organization=org,
            name="Test API Key",
            key_hash=key_hash,
            prefix=prefix,
        )
        assert api_key.is_active is True

    def test_expires_at_optional(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        plain_key, key_hash, prefix = APIKey.generate_key()
        api_key = APIKey.objects.create(
            organization=org,
            name="Test API Key",
            key_hash=key_hash,
            prefix=prefix,
        )
        assert api_key.expires_at is None

    def test_last_used_at_optional(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        plain_key, key_hash, prefix = APIKey.generate_key()
        api_key = APIKey.objects.create(
            organization=org,
            name="Test API Key",
            key_hash=key_hash,
            prefix=prefix,
        )
        assert api_key.last_used_at is None

    def test_created_by_optional(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        user = User.objects.create_user(email="creator@example.com", password="testpass123")
        plain_key, key_hash, prefix = APIKey.generate_key()
        api_key = APIKey.objects.create(
            organization=org,
            name="Test API Key",
            key_hash=key_hash,
            prefix=prefix,
            created_by=user,
        )
        assert api_key.created_by == user
