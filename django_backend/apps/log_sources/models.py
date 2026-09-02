import uuid

from django.db import models


class LogSource(models.Model):
    class SourceType(models.TextChoices):
        FILEBEAT = "filebeat", "Filebeat"
        FLUENTD = "fluentd", "Fluentd"
        KAFKA = "kafka", "Kafka"
        API = "api", "API"
        GITHUB = "github", "GitHub"
        PAGERDUTY = "pagerduty", "PagerDuty"
        CONFLUENCE = "confluence", "Confluence"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="log_sources",
    )
    name = models.CharField(max_length=255)
    source_type = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.API
    )
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "log_sources_logsource"
        ordering = ["-created_at"]
        verbose_name = "Log Source"
        verbose_name_plural = "Log Sources"
        indexes = [
            models.Index(fields=["project"]),
            models.Index(fields=["source_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.project.name} / {self.name} ({self.source_type})"
