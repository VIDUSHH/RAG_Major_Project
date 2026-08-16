import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        full_name="Test User",
    )


class TestTokenObtainPair:
    @pytest.mark.django_db
    def test_obtain_token_success(self, api_client, user):
        response = api_client.post(
            "/api/token/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert response.data["user"]["email"] == "test@example.com"
        assert response.data["user"]["full_name"] == "Test User"

    @pytest.mark.django_db
    def test_obtain_token_invalid_credentials(self, api_client, user):
        response = api_client.post(
            "/api/token/",
            {"email": "test@example.com", "password": "wrongpassword"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    @pytest.mark.django_db
    def test_obtain_token_nonexistent_user(self, api_client):
        response = api_client.post(
            "/api/token/",
            {"email": "nonexistent@example.com", "password": "testpass123"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_obtain_token_missing_fields(self, api_client):
        response = api_client.post(
            "/api/token/",
            {"email": "test@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestTokenRefresh:
    @pytest.mark.django_db
    def test_refresh_token_success(self, api_client, user):
        # First obtain tokens
        obtain_response = api_client.post(
            "/api/token/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )
        refresh_token = obtain_response.data["refresh"]

        # Then refresh
        response = api_client.post(
            "/api/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "message" in response.data

    @pytest.mark.django_db
    def test_refresh_token_invalid(self, api_client):
        response = api_client.post(
            "/api/token/refresh/",
            {"refresh": "invalid_refresh_token"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenVerify:
    @pytest.mark.django_db
    def test_verify_token_success(self, api_client, user):
        obtain_response = api_client.post(
            "/api/token/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )
        access_token = obtain_response.data["access"]

        response = api_client.post(
            "/api/token/verify/",
            {"token": access_token},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["valid"] is True

    @pytest.mark.django_db
    def test_verify_token_invalid(self, api_client):
        response = api_client.post(
            "/api/token/verify/",
            {"token": "invalid_token"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
