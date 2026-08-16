from django.urls import path

from . import views

app_name = "postmortems"

urlpatterns = [
    path("", views.postmortem_list, name="postmortem_list"),
    path("create/", views.postmortem_create, name="postmortem_create"),
    path("<uuid:pk>/", views.postmortem_detail, name="postmortem_detail"),
    path("<uuid:pk>/update/", views.postmortem_update, name="postmortem_update"),
    path("<uuid:pk>/delete/", views.postmortem_delete, name="postmortem_delete"),
    path(
        "<uuid:pk>/trigger-ingestion/",
        views.postmortem_trigger_ingestion,
        name="postmortem_trigger_ingestion",
    ),
]
