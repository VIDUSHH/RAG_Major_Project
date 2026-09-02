from django.urls import path

from . import views

app_name = "organizations"

urlpatterns = [
    path("", views.organization_list, name="organization_list"),
    path("create/", views.organization_create, name="organization_create"),
    path("<uuid:pk>/", views.organization_detail, name="organization_detail"),
    path("<uuid:pk>/update/", views.organization_update, name="organization_update"),
    path("<uuid:pk>/delete/", views.organization_delete, name="organization_delete"),
    path("<uuid:pk>/members/", views.organization_members, name="organization_members"),
]
