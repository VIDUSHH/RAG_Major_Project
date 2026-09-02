from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.organizations.models import Organization, OrganizationMembership


class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = "organizations/list.html"
    context_object_name = "organizations"
    paginate_by = 20

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        return (
            Organization.objects.filter(id__in=user_org_ids)
            .annotate(project_count=Count("projects"), member_count=Count("memberships"))
            .order_by("-created_at")
        )


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    template_name = "organizations/create.html"
    fields = ["name"]
    success_url = reverse_lazy("organization_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        OrganizationMembership.objects.create(
            user=self.request.user, organization=self.object, role=OrganizationMembership.Role.OWNER
        )
        messages.success(self.request, f'Organization "{self.object.name}" created successfully!')
        return response


class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "organizations/detail.html"
    context_object_name = "organization"

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        return Organization.objects.filter(id__in=user_org_ids)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.object
        context.update(
            {
                "projects": org.projects.all()[:10],
                "members": org.memberships.select_related("user").all(),
                "project_count": org.projects.count(),
                "member_count": org.memberships.count(),
                "user_role": org.memberships.get(user=self.request.user).role,
            }
        )
        return context


class OrganizationUpdateView(LoginRequiredMixin, UpdateView):
    model = Organization
    template_name = "organizations/update.html"
    fields = ["name"]
    success_url = reverse_lazy("organization_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
        ).values_list("organization_id", flat=True)
        return Organization.objects.filter(id__in=user_org_ids)

    def form_valid(self, form):
        messages.success(self.request, f'Organization "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class OrganizationDeleteView(LoginRequiredMixin, DeleteView):
    model = Organization
    template_name = "organizations/delete.html"
    success_url = reverse_lazy("organization_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user, role=OrganizationMembership.Role.OWNER
        ).values_list("organization_id", flat=True)
        return Organization.objects.filter(id__in=user_org_ids)

    def delete(self, request, *args, **kwargs):
        org = self.get_object()
        messages.success(request, f'Organization "{org.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def organization_members(request, pk):
    org = get_object_or_404(Organization, pk=pk)
    membership = org.memberships.filter(user=request.user).first()

    if not membership or membership.role not in [
        OrganizationMembership.Role.OWNER,
        OrganizationMembership.Role.ADMIN,
    ]:
        messages.error(request, "You do not have permission to manage members.")
        return redirect("organization_detail", pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")

        if action == "remove" and user_id:
            target_membership = org.memberships.filter(user_id=user_id).first()
            if target_membership and target_membership.user != request.user:
                target_membership.delete()
                messages.success(request, "Member removed successfully.")
            else:
                messages.error(request, "Cannot remove yourself or member not found.")
        elif action == "update_role" and user_id:
            new_role = request.POST.get("role")
            target_membership = org.memberships.filter(user_id=user_id).first()
            if target_membership and target_membership.user != request.user:
                target_membership.role = new_role
                target_membership.save()
                messages.success(request, "Role updated successfully.")
            else:
                messages.error(request, "Cannot change your own role or member not found.")

        return redirect("organization_members", pk=pk)

    members = org.memberships.select_related("user").all()
    return render(
        request,
        "organizations/members.html",
        {
            "organization": org,
            "members": members,
            "user_membership": membership,
            "roles": OrganizationMembership.Role.choices,
        },
    )


organization_list = OrganizationListView.as_view()
organization_create = OrganizationCreateView.as_view()
organization_detail = OrganizationDetailView.as_view()
organization_update = OrganizationUpdateView.as_view()
organization_delete = OrganizationDeleteView.as_view()
