import pytest

from apps.accounts.models import User
from apps.incidents.models import Incident
from apps.organizations.models import Organization
from apps.postmortems.models import Postmortem
from apps.projects.models import Project


@pytest.mark.django_db
class TestPostmortemModel:
    def test_postmortem_creation(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        incident = Incident.objects.create(project=project, title="Test Incident")
        postmortem = Postmortem.objects.create(
            incident=incident,
            title="Test Postmortem",
            document_source="/path/to/document.pdf",
        )
        assert postmortem.title == "Test Postmortem"
        assert postmortem.document_source == "/path/to/document.pdf"
        assert postmortem.incident == incident
        assert postmortem.id is not None

    def test_postmortem_str(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        incident = Incident.objects.create(project=project, title="Test Incident")
        postmortem = Postmortem.objects.create(
            incident=incident,
            title="Test Postmortem",
            document_source="/path/to/document.pdf",
        )
        assert str(postmortem) == "Postmortem: Test Postmortem"

    def test_status_choices(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        incident = Incident.objects.create(project=project, title="Test Incident")
        for status in Postmortem.IngestionStatus.choices:
            postmortem = Postmortem.objects.create(
                incident=incident,
                title=f"Postmortem {status[0]}",
                document_source="/path/to/document.pdf",
                ingestion_status=status[0],
            )
            assert postmortem.ingestion_status == status[0]

    def test_default_statuses(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        incident = Incident.objects.create(project=project, title="Test Incident")
        postmortem = Postmortem.objects.create(
            incident=incident,
            title="Test Postmortem",
            document_source="/path/to/document.pdf",
        )
        assert postmortem.ingestion_status == Postmortem.IngestionStatus.PENDING
        assert postmortem.processing_status == Postmortem.IngestionStatus.PENDING
        assert postmortem.embedding_status == Postmortem.IngestionStatus.PENDING
        assert postmortem.graph_indexing_status == Postmortem.IngestionStatus.PENDING

    def test_content_metadata_json_field(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        incident = Incident.objects.create(project=project, title="Test Incident")
        postmortem = Postmortem.objects.create(
            incident=incident,
            title="Test Postmortem",
            document_source="/path/to/document.pdf",
            content_metadata={"sections": ["root_cause", "timeline"], "word_count": 1500},
        )
        assert postmortem.content_metadata == {
            "sections": ["root_cause", "timeline"],
            "word_count": 1500,
        }

    def test_created_by_optional(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        incident = Incident.objects.create(project=project, title="Test Incident")
        user = User.objects.create_user(email="creator@example.com", password="testpass123")
        postmortem = Postmortem.objects.create(
            incident=incident,
            title="Test Postmortem",
            document_source="/path/to/document.pdf",
            created_by=user,
        )
        assert postmortem.created_by == user
