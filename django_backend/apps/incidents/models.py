import uuid

from django.conf import settings
from django.db import models


class Incident(models.Model):
    class Severity(models.TextChoices):
        P1 = "P1", "Critical"
        P2 = "P2", "High"
        P3 = "P3", "Medium"
        P4 = "P4", "Low"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INVESTIGATING = "investigating", "Investigating"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="incidents",
    )
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=2, choices=Severity.choices, default=Severity.P3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    started_at = models.DateTimeField(null=True, blank=True)
    detected_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    affected_services = models.ManyToManyField(
        "services.Service",
        related_name="incidents",
        blank=True,
    )
    suspected_root_cause = models.TextField(blank=True)
    confirmed_root_cause = models.TextField(blank=True)
    remediation = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_incidents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "incidents_incident"
        ordering = ["-created_at"]
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
        indexes = [
            models.Index(fields=["project"]),
            models.Index(fields=["severity"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["started_at"]),
            models.Index(fields=["detected_at"]),
            models.Index(fields=["resolved_at"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title}"
