from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.incidents.models import Incident
from apps.organizations.models import OrganizationMembership
from apps.projects.models import Project
from apps.services.models import Service


class IncidentListView(LoginRequiredMixin, ListView):
    model = Incident
    template_name = "incidents/list.html"
    context_object_name = "incidents"
    paginate_by = 20

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        queryset = (
            Incident.objects.filter(project__organization_id__in=user_org_ids)
            .select_related("project", "project__organization", "created_by")
            .prefetch_related("affected_services")
            .order_by("-created_at")
        )

        project_id = self.request.GET.get("project")
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        severity = self.request.GET.get("severity")
        if severity:
            queryset = queryset.filter(severity=severity)

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        context["projects"] = Project.objects.filter(
            organization_id__in=user_org_ids
        ).select_related("organization")
        context["statuses"] = Incident.Status.choices
        context["severities"] = Incident.Severity.choices
        context["selected_project"] = self.request.GET.get("project")
        context["selected_status"] = self.request.GET.get("status")
        context["selected_severity"] = self.request.GET.get("severity")
        context["search_query"] = self.request.GET.get("search", "")
        return context


class IncidentCreateView(LoginRequiredMixin, CreateView):
    model = Incident
    template_name = "incidents/create.html"
    fields = [
        "project",
        "title",
        "description",
        "severity",
        "status",
        "started_at",
        "detected_at",
        "affected_services",
        "suspected_root_cause",
    ]
    success_url = reverse_lazy("incident_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        form.fields["project"].queryset = Project.objects.filter(
            organization_id__in=user_org_ids
        ).select_related("organization")
        form.fields["affected_services"].queryset = Service.objects.filter(
            project__organization_id__in=user_org_ids
        )

        for field_name in ["started_at", "detected_at"]:
            form.fields[field_name].widget.attrs.update({"type": "datetime-local"})

        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Incident "{form.instance.title}" created successfully!')
        return super().form_valid(form)


class IncidentDetailView(LoginRequiredMixin, DetailView):
    model = Incident
    template_name = "incidents/detail.html"
    context_object_name = "incident"

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        return (
            Incident.objects.filter(project__organization_id__in=user_org_ids)
            .select_related("project", "project__organization", "created_by")
            .prefetch_related("affected_services", "postmortems")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        incident = self.object
        context.update(
            {
                "postmortems": incident.postmortems.all(),
                "can_edit": self.request.user == incident.created_by
                or incident.project.organization.memberships.filter(
                    user=self.request.user,
                    role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
                ).exists(),
            }
        )
        return context


class IncidentUpdateView(LoginRequiredMixin, UpdateView):
    model = Incident
    template_name = "incidents/update.html"
    fields = [
        "project",
        "title",
        "description",
        "severity",
        "status",
        "started_at",
        "detected_at",
        "resolved_at",
        "affected_services",
        "suspected_root_cause",
        "confirmed_root_cause",
        "remediation",
    ]
    success_url = reverse_lazy("incident_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[
                OrganizationMembership.Role.OWNER,
                OrganizationMembership.Role.ADMIN,
                OrganizationMembership.Role.ENGINEER,
            ],
        ).values_list("organization_id", flat=True)
        return Incident.objects.filter(project__organization_id__in=user_org_ids)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        form.fields["project"].queryset = Project.objects.filter(
            organization_id__in=user_org_ids
        ).select_related("organization")
        form.fields["affected_services"].queryset = Service.objects.filter(
            project__organization_id__in=user_org_ids
        )

        for field_name in ["started_at", "detected_at", "resolved_at"]:
            form.fields[field_name].widget.attrs.update({"type": "datetime-local"})

        return form

    def form_valid(self, form):
        if form.instance.status == Incident.Status.RESOLVED and not form.instance.resolved_at:
            form.instance.resolved_at = timezone.now()
        messages.success(self.request, f'Incident "{form.instance.title}" updated successfully!')
        return super().form_valid(form)


class IncidentDeleteView(LoginRequiredMixin, DeleteView):
    model = Incident
    template_name = "incidents/delete.html"
    success_url = reverse_lazy("incident_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
        ).values_list("organization_id", flat=True)
        return Incident.objects.filter(project__organization_id__in=user_org_ids)

    def delete(self, request, *args, **kwargs):
        incident = self.get_object()
        messages.success(request, f'Incident "{incident.title}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def incident_resolve(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    user_org_ids = OrganizationMembership.objects.filter(
        user=request.user,
        role__in=[
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.ADMIN,
            OrganizationMembership.Role.ENGINEER,
        ],
    ).values_list("organization_id", flat=True)

    if incident.project.organization_id not in user_org_ids:
        messages.error(request, "You do not have permission to resolve this incident.")
        return redirect("incident_detail", pk=pk)

    if request.method == "POST":
        incident.status = Incident.Status.RESOLVED
        incident.resolved_at = timezone.now()
        incident.confirmed_root_cause = request.POST.get("confirmed_root_cause", "")
        incident.remediation = request.POST.get("remediation", "")
        incident.save()
        messages.success(request, f'Incident "{incident.title}" marked as resolved!')
        return redirect("incident_detail", pk=pk)

    return render(request, "incidents/resolve.html", {"incident": incident})


incident_list = IncidentListView.as_view()
incident_create = IncidentCreateView.as_view()
incident_detail = IncidentDetailView.as_view()
incident_update = IncidentUpdateView.as_view()
incident_delete = IncidentDeleteView.as_view()
incident_resolve = incident_resolve
