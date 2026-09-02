from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.organizations.models import Organization, OrganizationMembership
from apps.postmortems.models import Postmortem
from apps.projects.models import Project


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "projects/list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        queryset = (
            Project.objects.filter(organization_id__in=user_org_ids)
            .select_related("organization")
            .annotate(
                service_count=Count("services"),
                incident_count=Count("incidents"),
                log_source_count=Count("log_sources"),
            )
            .order_by("-created_at")
        )

        org_id = self.request.GET.get("organization")
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        context["organizations"] = Organization.objects.filter(id__in=user_org_ids)
        context["selected_org"] = self.request.GET.get("organization")
        context["search_query"] = self.request.GET.get("search", "")
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    template_name = "projects/create.html"
    fields = ["organization", "name", "description"]
    success_url = reverse_lazy("project_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        form.fields["organization"].queryset = Organization.objects.filter(id__in=user_org_ids)
        return form

    def form_valid(self, form):
        messages.success(self.request, f'Project "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "projects/detail.html"
    context_object_name = "project"

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        return Project.objects.filter(organization_id__in=user_org_ids).select_related(
            "organization"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        context.update(
            {
                "services": project.services.all()[:10],
                "incidents": project.incidents.select_related("created_by").order_by("-created_at")[
                    :10
                ],
                "postmortems": Postmortem.objects.filter(incident__project=project)
                .select_related("incident")
                .order_by("-created_at")[:5],
                "log_sources": project.log_sources.all()[:10],
                "service_count": project.services.count(),
                "incident_count": project.incidents.count(),
                "open_incident_count": project.incidents.filter(
                    status__in=["open", "investigating"]
                ).count(),
                "log_source_count": project.log_sources.filter(is_active=True).count(),
                "user_role": project.organization.memberships.get(user=self.request.user).role,
            }
        )
        return context


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    template_name = "projects/update.html"
    fields = ["organization", "name", "description"]
    success_url = reverse_lazy("project_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[
                OrganizationMembership.Role.OWNER,
                OrganizationMembership.Role.ADMIN,
                OrganizationMembership.Role.ENGINEER,
            ],
        ).values_list("organization_id", flat=True)
        return Project.objects.filter(organization_id__in=user_org_ids)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        form.fields["organization"].queryset = Organization.objects.filter(id__in=user_org_ids)
        return form

    def form_valid(self, form):
        messages.success(self.request, f'Project "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = "projects/delete.html"
    success_url = reverse_lazy("project_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
        ).values_list("organization_id", flat=True)
        return Project.objects.filter(organization_id__in=user_org_ids)

    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        messages.success(request, f'Project "{project.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


project_list = ProjectListView.as_view()
project_create = ProjectCreateView.as_view()
project_detail = ProjectDetailView.as_view()
project_update = ProjectUpdateView.as_view()
project_delete = ProjectDeleteView.as_view()
