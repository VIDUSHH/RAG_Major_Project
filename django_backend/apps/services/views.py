from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.organizations.models import OrganizationMembership
from apps.projects.models import Project
from apps.services.models import Service


class ServiceListView(LoginRequiredMixin, ListView):
    model = Service
    template_name = "services/list.html"
    context_object_name = "services"
    paginate_by = 20

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        queryset = (
            Service.objects.filter(project__organization_id__in=user_org_ids)
            .select_related("project", "project__organization")
            .annotate(incident_count=Count("incidents"))
            .order_by("-created_at")
        )

        project_id = self.request.GET.get("project")
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        service_type = self.request.GET.get("service_type")
        if service_type:
            queryset = queryset.filter(service_type=service_type)

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        context["projects"] = Project.objects.filter(
            organization_id__in=user_org_ids
        ).select_related("organization")
        context["service_types"] = Service.ServiceType.choices
        context["selected_project"] = self.request.GET.get("project")
        context["selected_type"] = self.request.GET.get("service_type")
        context["search_query"] = self.request.GET.get("search", "")
        return context


class ServiceCreateView(LoginRequiredMixin, CreateView):
    model = Service
    template_name = "services/create.html"
    fields = ["project", "name", "description", "service_type", "repository_url"]
    success_url = reverse_lazy("service_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        form.fields["project"].queryset = Project.objects.filter(
            organization_id__in=user_org_ids
        ).select_related("organization")
        return form

    def form_valid(self, form):
        messages.success(self.request, f'Service "{form.instance.name}" registered successfully!')
        return super().form_valid(form)


class ServiceDetailView(LoginRequiredMixin, DetailView):
    model = Service
    template_name = "services/detail.html"
    context_object_name = "service"

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        return Service.objects.filter(project__organization_id__in=user_org_ids).select_related(
            "project", "project__organization"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.object
        context.update(
            {
                "incidents": service.incidents.select_related("project", "created_by").order_by(
                    "-created_at"
                )[:20],
                "incident_count": service.incidents.count(),
                "open_incident_count": service.incidents.filter(
                    status__in=["open", "investigating"]
                ).count(),
            }
        )
        return context


class ServiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Service
    template_name = "services/update.html"
    fields = ["project", "name", "description", "service_type", "repository_url"]
    success_url = reverse_lazy("service_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[
                OrganizationMembership.Role.OWNER,
                OrganizationMembership.Role.ADMIN,
                OrganizationMembership.Role.ENGINEER,
            ],
        ).values_list("organization_id", flat=True)
        return Service.objects.filter(project__organization_id__in=user_org_ids)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        form.fields["project"].queryset = Project.objects.filter(
            organization_id__in=user_org_ids
        ).select_related("organization")
        return form

    def form_valid(self, form):
        messages.success(self.request, f'Service "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class ServiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Service
    template_name = "services/delete.html"
    success_url = reverse_lazy("service_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
        ).values_list("organization_id", flat=True)
        return Service.objects.filter(project__organization_id__in=user_org_ids)

    def delete(self, request, *args, **kwargs):
        service = self.get_object()
        messages.success(request, f'Service "{service.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


service_list = ServiceListView.as_view()
service_create = ServiceCreateView.as_view()
service_detail = ServiceDetailView.as_view()
service_update = ServiceUpdateView.as_view()
service_delete = ServiceDeleteView.as_view()
