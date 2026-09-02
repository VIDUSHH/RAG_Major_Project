import pytest

from apps.accounts.models import User
from apps.incidents.models import Incident
from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.services.models import Service


@pytest.mark.django_db
class TestIncidentModel:
    def test_incident_creation(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        incident = Incident.objects.create(
            project=project,
            title="Test Incident",
            description="Test Description",
            severity=Incident.Severity.P1,
            status=Incident.Status.OPEN,
        )
        assert incident.title == "Test Incident"
        assert incident.severity == Incident.Severity.P1
        assert incident.status == Incident.Status.OPEN
        assert incident.id is not None

    def test_incident_str(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        incident = Incident.objects.create(
            project=project, title="Test Incident", severity=Incident.Severity.P2
        )
        assert str(incident) == "[P2] Test Incident"

    def test_severity_choices(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        for severity in Incident.Severity.choices:
            incident = Incident.objects.create(
                project=project,
                title=f"Incident {severity[0]}",
                severity=severity[0],
            )
            assert incident.severity == severity[0]

    def test_status_choices(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        for status in Incident.Status.choices:
            incident = Incident.objects.create(
                project=project,
                title=f"Incident {status[0]}",
                status=status[0],
            )
            assert incident.status == status[0]

    def test_default_severity_and_status(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        incident = Incident.objects.create(project=project, title="Test Incident")
        assert incident.severity == Incident.Severity.P3
        assert incident.status == Incident.Status.OPEN

    def test_affected_services_m2m(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        service1 = Service.objects.create(
            project=project, name="Service 1", service_type=Service.ServiceType.WEB
        )
        service2 = Service.objects.create(
            project=project, name="Service 2", service_type=Service.ServiceType.DATABASE
        )
        incident = Incident.objects.create(project=project, title="Test Incident")
        incident.affected_services.add(service1, service2)
        assert incident.affected_services.count() == 2
        assert service1 in incident.affected_services.all()
        assert service2 in incident.affected_services.all()

    def test_metadata_json_field(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        incident = Incident.objects.create(
            project=project,
            title="Test Incident",
            metadata={"key": "value", "count": 42},
        )
        assert incident.metadata == {"key": "value", "count": 42}

    def test_created_by_optional(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        user = User.objects.create_user(email="creator@example.com", password="testpass123")
        incident = Incident.objects.create(project=project, title="Test Incident", created_by=user)
        assert incident.created_by == user
