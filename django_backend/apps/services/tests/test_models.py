import pytest

from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.services.models import Service


@pytest.mark.django_db
class TestServiceModel:
    def test_service_creation(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        service = Service.objects.create(
            project=project,
            name="Test Service",
            service_type=Service.ServiceType.WEB,
            repository_url="https://github.com/test/repo",
        )
        assert service.name == "Test Service"
        assert service.service_type == Service.ServiceType.WEB
        assert service.repository_url == "https://github.com/test/repo"
        assert service.project == project
        assert service.id is not None

    def test_service_str(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        service = Service.objects.create(
            project=project,
            name="Test Service",
            service_type=Service.ServiceType.DATABASE,
        )
        assert str(service) == "Test Org / Test Project / Test Service"

    def test_service_type_choices(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        for service_type in Service.ServiceType.choices:
            service = Service.objects.create(
                project=project,
                name=f"Service {service_type[0]}",
                service_type=service_type[0],
            )
            assert service.service_type == service_type[0]

    def test_default_service_type(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        service = Service.objects.create(project=project, name="Test Service")
        assert service.service_type == Service.ServiceType.OTHER

    def test_repository_url_optional(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        service = Service.objects.create(project=project, name="Test Service")
        assert service.repository_url == ""
