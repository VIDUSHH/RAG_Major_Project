import uuid

from django.conf import settings
from django.db import models


class Postmortem(models.Model):
    class IngestionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.CASCADE,
        related_name="postmortems",
    )
    title = models.CharField(max_length=500)
    document_source = models.CharField(max_length=1000)
    content_metadata = models.JSONField(default=dict, blank=True)
    ingestion_status = models.CharField(
        max_length=20,
        choices=IngestionStatus.choices,
        default=IngestionStatus.PENDING,
    )
    processing_status = models.CharField(
        max_length=20,
        choices=IngestionStatus.choices,
        default=IngestionStatus.PENDING,
    )
    embedding_status = models.CharField(
        max_length=20,
        choices=IngestionStatus.choices,
        default=IngestionStatus.PENDING,
    )
    graph_indexing_status = models.CharField(
        max_length=20,
        choices=IngestionStatus.choices,
        default=IngestionStatus.PENDING,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_postmortems",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "postmortems_postmortem"
        ordering = ["-created_at"]
        verbose_name = "Postmortem"
        verbose_name_plural = "Postmortems"
        indexes = [
            models.Index(fields=["incident"]),
            models.Index(fields=["ingestion_status"]),
            models.Index(fields=["processing_status"]),
            models.Index(fields=["embedding_status"]),
            models.Index(fields=["graph_indexing_status"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self):
        return f"Postmortem: {self.title}"
