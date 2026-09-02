import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.log_sources.models import LogSource
from apps.organizations.models import OrganizationMembership
from apps.projects.models import Project


class LogSourceListView(LoginRequiredMixin, ListView):
    model = LogSource
    template_name = "log_sources/list.html"
    context_object_name = "log_sources"
    paginate_by = 20

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        queryset = (
            LogSource.objects.filter(project__organization_id__in=user_org_ids)
            .select_related("project", "project__organization")
            .order_by("-created_at")
        )

        project_id = self.request.GET.get("project")
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        source_type = self.request.GET.get("source_type")
        if source_type:
            queryset = queryset.filter(source_type=source_type)

        is_active = self.request.GET.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == "true")

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(Q(name__icontains=search))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        context["projects"] = Project.objects.filter(
            organization_id__in=user_org_ids
        ).select_related("organization")
        context["source_types"] = LogSource.SourceType.choices
        context["selected_project"] = self.request.GET.get("project")
        context["selected_type"] = self.request.GET.get("source_type")
        context["selected_active"] = self.request.GET.get("is_active")
        context["search_query"] = self.request.GET.get("search", "")
        return context


class LogSourceCreateView(LoginRequiredMixin, CreateView):
    model = LogSource
    template_name = "log_sources/create.html"
    fields = ["project", "name", "source_type", "config", "is_active"]
    success_url = reverse_lazy("logsource_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        form.fields["project"].queryset = Project.objects.filter(
            organization_id__in=user_org_ids
        ).select_related("organization")
        form.fields["config"].widget.attrs.update({"rows": 10, "placeholder": '{"key": "value"}'})
        return form

    def form_valid(self, form):
        try:
            json.loads(form.instance.config) if form.instance.config else {}
        except json.JSONDecodeError:
            form.add_error("config", "Invalid JSON format")
            return self.form_invalid(form)

        messages.success(self.request, f'Log source "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class LogSourceDetailView(LoginRequiredMixin, DetailView):
    model = LogSource
    template_name = "log_sources/detail.html"
    context_object_name = "log_source"

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        return LogSource.objects.filter(project__organization_id__in=user_org_ids).select_related(
            "project", "project__organization"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        log_source = self.object
        try:
            context["config_json"] = json.dumps(log_source.config, indent=2)
        except (TypeError, ValueError):
            context["config_json"] = "Invalid JSON"
        return context


class LogSourceUpdateView(LoginRequiredMixin, UpdateView):
    model = LogSource
    template_name = "log_sources/update.html"
    fields = ["project", "name", "source_type", "config", "is_active"]
    success_url = reverse_lazy("logsource_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[
                OrganizationMembership.Role.OWNER,
                OrganizationMembership.Role.ADMIN,
                OrganizationMembership.Role.ENGINEER,
            ],
        ).values_list("organization_id", flat=True)
        return LogSource.objects.filter(project__organization_id__in=user_org_ids)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        form.fields["project"].queryset = Project.objects.filter(
            organization_id__in=user_org_ids
        ).select_related("organization")
        form.fields["config"].widget.attrs.update({"rows": 10})
        return form

    def form_valid(self, form):
        try:
            json.loads(form.instance.config) if form.instance.config else {}
        except json.JSONDecodeError:
            form.add_error("config", "Invalid JSON format")
            return self.form_invalid(form)

        messages.success(self.request, f'Log source "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class LogSourceDeleteView(LoginRequiredMixin, DeleteView):
    model = LogSource
    template_name = "log_sources/delete.html"
    success_url = reverse_lazy("logsource_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
        ).values_list("organization_id", flat=True)
        return LogSource.objects.filter(project__organization_id__in=user_org_ids)

    def delete(self, request, *args, **kwargs):
        log_source = self.get_object()
        messages.success(request, f'Log source "{log_source.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def logsource_toggle_active(request, pk):
    log_source = get_object_or_404(LogSource, pk=pk)
    user_org_ids = OrganizationMembership.objects.filter(
        user=request.user,
        role__in=[
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.ADMIN,
            OrganizationMembership.Role.ENGINEER,
        ],
    ).values_list("organization_id", flat=True)

    if log_source.project.organization_id not in user_org_ids:
        messages.error(request, "You do not have permission to modify this log source.")
        return redirect("logsource_detail", pk=pk)

    log_source.is_active = not log_source.is_active
    log_source.save()

    status = "activated" if log_source.is_active else "deactivated"
    messages.success(request, f'Log source "{log_source.name}" {status} successfully!')
    return redirect("logsource_detail", pk=pk)


logsource_list = LogSourceListView.as_view()
logsource_create = LogSourceCreateView.as_view()
logsource_detail = LogSourceDetailView.as_view()
logsource_update = LogSourceUpdateView.as_view()
logsource_delete = LogSourceDeleteView.as_view()
logsource_toggle_active = logsource_toggle_active
