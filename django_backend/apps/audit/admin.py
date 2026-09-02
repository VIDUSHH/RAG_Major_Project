from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "user",
        "action",
        "resource_type",
        "resource_id",
        "created_at",
    )
    list_filter = ("action", "resource_type", "organization")
    search_fields = (
        "user__email",
        "resource_id",
        "organization__name",
        "ip_address",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "organization",
        "user",
        "action",
        "resource_type",
        "resource_id",
        "changes",
        "ip_address",
        "user_agent",
        "created_at",
    )
    raw_id_fields = ("organization", "user")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
