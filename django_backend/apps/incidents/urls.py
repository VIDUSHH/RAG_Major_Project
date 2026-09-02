from django.urls import path

from . import views

app_name = "incidents"

urlpatterns = [
    path("", views.incident_list, name="incident_list"),
    path("create/", views.incident_create, name="incident_create"),
    path("<uuid:pk>/", views.incident_detail, name="incident_detail"),
    path("<uuid:pk>/update/", views.incident_update, name="incident_update"),
    path("<uuid:pk>/delete/", views.incident_delete, name="incident_delete"),
    path("<uuid:pk>/resolve/", views.incident_resolve, name="incident_resolve"),
]
