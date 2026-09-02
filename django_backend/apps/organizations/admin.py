from django.contrib import admin

from .models import Organization, OrganizationMembership


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at", "updated_at")
    search_fields = ("name", "slug")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "joined_at")
    list_filter = ("role", "organization")
    search_fields = ("user__email", "user__full_name", "organization__name")
    ordering = ("-joined_at",)
    readonly_fields = ("joined_at",)
    raw_id_fields = ("user", "organization")
