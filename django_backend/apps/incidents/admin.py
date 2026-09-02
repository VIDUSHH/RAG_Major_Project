from django.contrib import admin

from .models import Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "project",
        "severity",
        "status",
        "started_at",
        "detected_at",
        "resolved_at",
        "created_at",
    )
    list_filter = ("severity", "status", "project__organization", "project")
    search_fields = ("title", "description", "project__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("project", "created_by")
    filter_horizontal = ("affected_services",)
