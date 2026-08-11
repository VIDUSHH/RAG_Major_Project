from django.contrib import admin
from django.urls import path
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({
        "status": "healthy",
        "service": "django_control_plane",
        "version": "1.0.0"
    })

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
]
