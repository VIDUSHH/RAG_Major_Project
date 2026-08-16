from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "service_type", "repository_url", "created_at")
    list_filter = ("service_type", "project__organization")
    search_fields = ("name", "project__name", "repository_url")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    raw_id_fields = ("project",)
