from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.utils import timezone
from django.views.generic import ListView

from apps.incidents.models import Incident
from apps.log_sources.models import LogSource
from apps.organizations.models import Organization, OrganizationMembership
from apps.postmortems.models import Postmortem
from apps.projects.models import Project
from apps.services.models import Service


class DashboardView(LoginRequiredMixin, ListView):
    template_name = "dashboard/index.html"
    context_object_name = "recent_incidents"

    def get_queryset(self):
        user_orgs = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        return (
            Incident.objects.filter(project__organization_id__in=user_orgs)
            .select_related("project", "created_by")
            .order_by("-created_at")[:10]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_orgs = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )

        now = timezone.now()
        week_ago = now - timedelta(days=7)

        context.update(
            {
                "stats": {
                    "organizations": Organization.objects.filter(id__in=user_orgs).count(),
                    "projects": Project.objects.filter(organization_id__in=user_orgs).count(),
                    "services": Service.objects.filter(
                        project__organization_id__in=user_orgs
                    ).count(),
                    "incidents_open": Incident.objects.filter(
                        project__organization_id__in=user_orgs, status__in=["open", "investigating"]
                    ).count(),
                    "incidents_week": Incident.objects.filter(
                        project__organization_id__in=user_orgs, created_at__gte=week_ago
                    ).count(),
                    "postmortems": Postmortem.objects.filter(
                        incident__project__organization_id__in=user_orgs
                    ).count(),
                    "postmortems_pending": Postmortem.objects.filter(
                        incident__project__organization_id__in=user_orgs, ingestion_status="pending"
                    ).count(),
                    "log_sources": LogSource.objects.filter(
                        project__organization_id__in=user_orgs, is_active=True
                    ).count(),
                },
                "recent_incidents": self.get_queryset(),
                "recent_postmortems": Postmortem.objects.filter(
                    incident__project__organization_id__in=user_orgs
                )
                .select_related("incident", "incident__project")
                .order_by("-created_at")[:5],
                "severity_counts": Incident.objects.filter(
                    project__organization_id__in=user_orgs, status__in=["open", "investigating"]
                )
                .values("severity")
                .annotate(count=Count("id")),
            }
        )
        return context


dashboard = DashboardView.as_view()
