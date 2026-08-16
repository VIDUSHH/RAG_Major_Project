import pytest
from django.db import IntegrityError

from apps.organizations.models import Organization
from apps.projects.models import Project


@pytest.mark.django_db
class TestProjectModel:
    def test_project_creation(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        assert project.name == "Test Project"
        assert project.slug == "test-project"
        assert project.organization == org
        assert project.id is not None

    def test_project_str(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        assert str(project) == "Test Org / Test Project"

    def test_unique_organization_slug_constraint(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        Project.objects.create(organization=org, name="Test Project 1", slug="test-project")
        with pytest.raises(IntegrityError):
            Project.objects.create(organization=org, name="Test Project 2", slug="test-project")

    def test_same_slug_different_org_allowed(self):
        org1 = Organization.objects.create(name="Test Org 1", slug="test-org-1")
        org2 = Organization.objects.create(name="Test Org 2", slug="test-org-2")
        Project.objects.create(organization=org1, name="Test Project", slug="test-project")
        project2 = Project.objects.create(
            organization=org2, name="Test Project", slug="test-project"
        )
        assert project2.slug == "test-project"

    def test_project_description_optional(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        assert project.description == ""
