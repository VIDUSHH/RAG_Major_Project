from django.contrib import admin

from .models import Postmortem


@admin.register(Postmortem)
class PostmortemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "incident",
        "ingestion_status",
        "processing_status",
        "embedding_status",
        "graph_indexing_status",
        "created_at",
    )
    list_filter = (
        "ingestion_status",
        "processing_status",
        "embedding_status",
        "graph_indexing_status",
        "incident__project__organization",
    )
    search_fields = ("title", "incident__title", "document_source")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("incident", "created_by")
