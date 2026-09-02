from django.contrib import admin

from .models import LogSource


@admin.register(LogSource)
class LogSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "source_type", "is_active", "created_at")
    list_filter = ("source_type", "is_active", "project__organization")
    search_fields = ("name", "project__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    raw_id_fields = ("project",)
