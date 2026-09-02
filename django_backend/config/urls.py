from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.accounts.views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenVerifyView,
)
from apps.core.views import dashboard


def health_check(request):
    return JsonResponse(
        {"status": "healthy", "service": "django_control_plane", "version": "1.0.0"}
    )


urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    # JWT Authentication endpoints
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", CustomTokenVerifyView.as_view(), name="token_verify"),
    # Web UI Routes
    path("organizations/", include("apps.organizations.urls")),
    path("projects/", include("apps.projects.urls")),
    path("services/", include("apps.services.urls")),
    path("incidents/", include("apps.incidents.urls")),
    path("postmortems/", include("apps.postmortems.urls")),
    path("log-sources/", include("apps.log_sources.urls")),
    path("accounts/", include("apps.accounts.urls")),
]
