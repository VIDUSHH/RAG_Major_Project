from django.contrib import admin

from .models import APIKey


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "prefix",
        "is_active",
        "expires_at",
        "last_used_at",
        "created_at",
    )
    list_filter = ("is_active", "organization")
    search_fields = ("name", "prefix", "organization__name")
    ordering = ("-created_at",)
    readonly_fields = ("key_hash", "prefix", "created_at", "last_used_at")
    raw_id_fields = ("organization", "created_by")

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return False
        return True
