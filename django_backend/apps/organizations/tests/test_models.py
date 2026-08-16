import pytest
from django.db import IntegrityError

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership


@pytest.mark.django_db
class TestOrganizationModel:
    def test_organization_creation(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        assert org.name == "Test Org"
        assert org.slug == "test-org"
        assert org.id is not None

    def test_organization_str(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        assert str(org) == "Test Org"

    def test_slug_unique_constraint(self):
        Organization.objects.create(name="Test Org 1", slug="test-org")
        with pytest.raises(IntegrityError):
            Organization.objects.create(name="Test Org 2", slug="test-org")

    def test_slug_auto_population(self):
        org = Organization.objects.create(name="Auto Slug Org")
        assert org.slug == "auto-slug-org"


@pytest.mark.django_db
class TestOrganizationMembershipModel:
    def test_membership_creation(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        org = Organization.objects.create(name="Test Org", slug="test-org")
        membership = OrganizationMembership.objects.create(
            user=user, organization=org, role=OrganizationMembership.Role.ENGINEER
        )
        assert membership.user == user
        assert membership.organization == org
        assert membership.role == OrganizationMembership.Role.ENGINEER

    def test_membership_str(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        org = Organization.objects.create(name="Test Org", slug="test-org")
        membership = OrganizationMembership.objects.create(
            user=user, organization=org, role=OrganizationMembership.Role.ADMIN
        )
        expected = f"test@example.com - Test Org ({OrganizationMembership.Role.ADMIN})"
        assert str(membership) == expected

    def test_unique_user_organization_constraint(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        org = Organization.objects.create(name="Test Org", slug="test-org")
        OrganizationMembership.objects.create(
            user=user, organization=org, role=OrganizationMembership.Role.VIEWER
        )
        with pytest.raises(IntegrityError):
            OrganizationMembership.objects.create(
                user=user, organization=org, role=OrganizationMembership.Role.ADMIN
            )

    def test_role_choices(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        for role in OrganizationMembership.Role.choices:
            membership = OrganizationMembership.objects.create(
                user=User.objects.create_user(
                    email=f"user{role[0]}@example.com", password="testpass123"
                ),
                organization=org,
                role=role[0],
            )
            assert membership.role == role[0]
