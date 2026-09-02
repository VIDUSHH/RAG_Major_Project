from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "slug", "created_at", "updated_at")
    list_filter = ("organization",)
    search_fields = ("name", "slug", "organization__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("organization",)
    prepopulated_fields = {"slug": ("name",)}
