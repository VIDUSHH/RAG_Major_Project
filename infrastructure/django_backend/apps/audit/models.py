import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        DELETED = "deleted", "Deleted"
        VIEWED = "viewed", "Viewed"
        INGESTED = "ingested", "Ingested"
        EXPORTED = "exported", "Exported"

    class ResourceType(models.TextChoices):
        INCIDENT = "Incident", "Incident"
        POSTMORTEM = "Postmortem", "Postmortem"
        PROJECT = "Project", "Project"
        SERVICE = "Service", "Service"
        ORGANIZATION = "Organization", "Organization"
        USER = "User", "User"
        LOG_SOURCE = "LogSource", "Log Source"
        API_KEY = "APIKey", "API Key"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    resource_type = models.CharField(max_length=30, choices=ResourceType.choices)
    resource_id = models.CharField(max_length=100)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_auditlog"
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["user"]),
            models.Index(fields=["action"]),
            models.Index(fields=["resource_type"]),
            models.Index(fields=["resource_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.user} - {self.action} {self.resource_type} {self.resource_id}"  # noqa: E501
