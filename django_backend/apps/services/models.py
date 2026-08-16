import uuid

from django.db import models


class Service(models.Model):
    class ServiceType(models.TextChoices):
        WEB = "web", "Web Service"
        DATABASE = "database", "Database"
        QUEUE = "queue", "Message Queue"
        CACHE = "cache", "Cache"
        STORAGE = "storage", "Storage"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="services",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    service_type = models.CharField(
        max_length=20, choices=ServiceType.choices, default=ServiceType.OTHER
    )
    repository_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "services_service"
        ordering = ["-created_at"]
        verbose_name = "Service"
        verbose_name_plural = "Services"
        indexes = [
            models.Index(fields=["project"]),
            models.Index(fields=["service_type"]),
        ]

    def __str__(self):
        return f"{self.project.organization.name} / {self.project.name} / {self.name}"
