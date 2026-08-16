import uuid

from django.db import models


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "projects_project"
        ordering = ["-created_at"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"], name="unique_organization_project_slug"
            ),
        ]
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return f"{self.organization.name} / {self.name}"
