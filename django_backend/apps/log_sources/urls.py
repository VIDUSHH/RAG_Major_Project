from django.urls import path

from . import views

app_name = "log_sources"

urlpatterns = [
    path("", views.logsource_list, name="logsource_list"),
    path("create/", views.logsource_create, name="logsource_create"),
    path("<uuid:pk>/", views.logsource_detail, name="logsource_detail"),
    path("<uuid:pk>/update/", views.logsource_update, name="logsource_update"),
    path("<uuid:pk>/delete/", views.logsource_delete, name="logsource_delete"),
    path("<uuid:pk>/toggle-active/", views.logsource_toggle_active, name="logsource_toggle_active"),
]
