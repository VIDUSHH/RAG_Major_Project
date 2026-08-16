import pytest

from apps.log_sources.models import LogSource
from apps.organizations.models import Organization
from apps.projects.models import Project


@pytest.mark.django_db
class TestLogSourceModel:
    def test_log_source_creation(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        log_source = LogSource.objects.create(
            project=project,
            name="Test Log Source",
            source_type=LogSource.SourceType.KAFKA,
            config={"topic": "logs", "bootstrap_servers": "localhost:9092"},
        )
        assert log_source.name == "Test Log Source"
        assert log_source.source_type == LogSource.SourceType.KAFKA
        assert log_source.config == {"topic": "logs", "bootstrap_servers": "localhost:9092"}
        assert log_source.is_active is True
        assert log_source.id is not None

    def test_log_source_str(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        log_source = LogSource.objects.create(
            project=project,
            name="Test Log Source",
            source_type=LogSource.SourceType.FILEBEAT,
        )
        assert str(log_source) == "Test Project / Test Log Source (filebeat)"

    def test_source_type_choices(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        for source_type in LogSource.SourceType.choices:
            log_source = LogSource.objects.create(
                project=project,
                name=f"Log Source {source_type[0]}",
                source_type=source_type[0],
            )
            assert log_source.source_type == source_type[0]

    def test_default_source_type(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        log_source = LogSource.objects.create(project=project, name="Test Log Source")
        assert log_source.source_type == LogSource.SourceType.API

    def test_config_json_field(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        log_source = LogSource.objects.create(
            project=project,
            name="Test Log Source",
            source_type=LogSource.SourceType.GITHUB,
            config={"repo": "org/repo", "branch": "main", "paths": ["logs/"]},
        )
        assert log_source.config == {"repo": "org/repo", "branch": "main", "paths": ["logs/"]}

    def test_is_active_default(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        log_source = LogSource.objects.create(project=project, name="Test Log Source")
        assert log_source.is_active is True

    def test_is_active_can_be_false(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        project = Project.objects.create(organization=org, name="Test Project", slug="test-project")
        log_source = LogSource.objects.create(
            project=project, name="Test Log Source", is_active=False
        )
        assert log_source.is_active is False
