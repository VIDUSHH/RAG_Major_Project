import pytest

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.organizations.models import Organization


@pytest.mark.django_db
class TestAuditLogModel:
    def test_audit_log_creation(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        audit_log = AuditLog.objects.create(
            organization=org,
            user=user,
            action=AuditLog.Action.CREATED,
            resource_type=AuditLog.ResourceType.INCIDENT,
            resource_id="incident-uuid-123",
            changes={"field": "value"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        assert audit_log.organization == org
        assert audit_log.user == user
        assert audit_log.action == AuditLog.Action.CREATED
        assert audit_log.resource_type == AuditLog.ResourceType.INCIDENT
        assert audit_log.resource_id == "incident-uuid-123"
        assert audit_log.changes == {"field": "value"}
        assert audit_log.ip_address == "192.168.1.1"
        assert audit_log.user_agent == "Mozilla/5.0"
        assert audit_log.id is not None

    def test_audit_log_str(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        audit_log = AuditLog.objects.create(
            organization=org,
            user=user,
            action=AuditLog.Action.UPDATED,
            resource_type=AuditLog.ResourceType.PROJECT,
            resource_id="project-uuid-456",
        )
        expected = f"Test Org - test@example.com - {AuditLog.Action.UPDATED} {AuditLog.ResourceType.PROJECT} project-uuid-456"  # noqa: E501
        assert str(audit_log) == expected

    def test_action_choices(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        for action in AuditLog.Action.choices:
            audit_log = AuditLog.objects.create(
                organization=org,
                action=action[0],
                resource_type=AuditLog.ResourceType.USER,
                resource_id="user-uuid-123",
            )
            assert audit_log.action == action[0]

    def test_resource_type_choices(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        for resource_type in AuditLog.ResourceType.choices:
            audit_log = AuditLog.objects.create(
                organization=org,
                action=AuditLog.Action.CREATED,
                resource_type=resource_type[0],
                resource_id=f"{resource_type[0].lower()}-uuid-123",
            )
            assert audit_log.resource_type == resource_type[0]

    def test_user_optional(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        audit_log = AuditLog.objects.create(
            organization=org,
            action=AuditLog.Action.INGESTED,
            resource_type=AuditLog.ResourceType.INCIDENT,
            resource_id="incident-uuid-123",
        )
        assert audit_log.user is None

    def test_changes_json_field(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        audit_log = AuditLog.objects.create(
            organization=org,
            action=AuditLog.Action.UPDATED,
            resource_type=AuditLog.ResourceType.SERVICE,
            resource_id="service-uuid-123",
            changes={"before": {"name": "old"}, "after": {"name": "new"}},
        )
        assert audit_log.changes == {"before": {"name": "old"}, "after": {"name": "new"}}

    def test_ip_address_optional(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        audit_log = AuditLog.objects.create(
            organization=org,
            action=AuditLog.Action.CREATED,
            resource_type=AuditLog.ResourceType.ORGANIZATION,
            resource_id="org-uuid-123",
        )
        assert audit_log.ip_address is None

    def test_user_agent_optional(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        audit_log = AuditLog.objects.create(
            organization=org,
            action=AuditLog.Action.CREATED,
            resource_type=AuditLog.ResourceType.ORGANIZATION,
            resource_id="org-uuid-123",
        )
        assert audit_log.user_agent == ""
