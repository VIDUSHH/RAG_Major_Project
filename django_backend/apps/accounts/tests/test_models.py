import pytest
from django.db import IntegrityError

from apps.accounts.models import User


@pytest.mark.django_db
class TestUserManager:
    def test_create_user(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert user.is_active is True
        assert user.is_staff is False

    def test_create_user_without_email_raises_error(self):
        with pytest.raises(ValueError, match="The Email field must be set"):
            User.objects.create_user(email="", password="testpass123")

    def test_create_superuser(self):
        user = User.objects.create_superuser(email="admin@example.com", password="adminpass123")
        assert user.email == "admin@example.com"
        assert user.check_password("adminpass123")
        assert user.is_active is True
        assert user.is_staff is True
        assert user.is_superuser is True


@pytest.mark.django_db
class TestUserModel:
    def test_user_str(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        assert str(user) == "test@example.com"

    def test_user_full_name(self):
        user = User.objects.create_user(
            email="test@example.com", password="testpass123", full_name="Test User"
        )
        assert user.get_full_name() == "Test User"
        assert user.get_short_name() == "Test"

    def test_user_without_full_name(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        assert user.get_full_name() == "test@example.com"
        assert user.get_short_name() == "test"

    def test_email_unique_constraint(self):
        User.objects.create_user(email="test@example.com", password="testpass123")
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="test@example.com", password="testpass456")

    def test_user_fields(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            full_name="Test User",
            is_active=False,
            is_staff=True,
        )
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is False
        assert user.is_staff is True
        assert user.id is not None
