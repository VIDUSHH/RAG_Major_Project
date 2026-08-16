import json
import logging

from asgiref.sync import async_to_sync
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.clients import get_fastapi_client
from apps.incidents.models import Incident
from apps.organizations.models import OrganizationMembership
from apps.postmortems.models import Postmortem
from apps.projects.models import Project

logger = logging.getLogger(__name__)


class PostmortemListView(LoginRequiredMixin, ListView):
    model = Postmortem
    template_name = "postmortems/list.html"
    context_object_name = "postmortems"
    paginate_by = 20

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        queryset = (
            Postmortem.objects.filter(incident__project__organization_id__in=user_org_ids)
            .select_related(
                "incident", "incident__project", "incident__project__organization", "created_by"
            )
            .order_by("-created_at")
        )

        project_id = self.request.GET.get("project")
        if project_id:
            queryset = queryset.filter(incident__project_id=project_id)

        ingestion_status = self.request.GET.get("ingestion_status")
        if ingestion_status:
            queryset = queryset.filter(ingestion_status=ingestion_status)

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(document_source__icontains=search)
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
        context["ingestion_statuses"] = Postmortem.IngestionStatus.choices
        context["selected_project"] = self.request.GET.get("project")
        context["selected_status"] = self.request.GET.get("ingestion_status")
        context["search_query"] = self.request.GET.get("search", "")
        return context


class PostmortemCreateView(LoginRequiredMixin, CreateView):
    model = Postmortem
    template_name = "postmortems/create.html"
    fields = ["incident", "title", "document_source", "content_metadata"]
    success_url = reverse_lazy("postmortem_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        form.fields["incident"].queryset = (
            Incident.objects.filter(project__organization_id__in=user_org_ids)
            .select_related("project", "project__organization")
            .order_by("-created_at")
        )
        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Postmortem "{form.instance.title}" created successfully!')
        return super().form_valid(form)


class PostmortemDetailView(LoginRequiredMixin, DetailView):
    model = Postmortem
    template_name = "postmortems/detail.html"
    context_object_name = "postmortem"

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        return Postmortem.objects.filter(
            incident__project__organization_id__in=user_org_ids
        ).select_related(
            "incident", "incident__project", "incident__project__organization", "created_by"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        postmortem = self.object
        context.update(
            {
                "incident": postmortem.incident,
                "can_trigger_ingestion": postmortem.ingestion_status
                in [Postmortem.IngestionStatus.PENDING, Postmortem.IngestionStatus.FAILED],
            }
        )
        return context


class PostmortemUpdateView(LoginRequiredMixin, UpdateView):
    model = Postmortem
    template_name = "postmortems/update.html"
    fields = ["incident", "title", "document_source", "content_metadata"]
    success_url = reverse_lazy("postmortem_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[
                OrganizationMembership.Role.OWNER,
                OrganizationMembership.Role.ADMIN,
                OrganizationMembership.Role.ENGINEER,
            ],
        ).values_list("organization_id", flat=True)
        return Postmortem.objects.filter(incident__project__organization_id__in=user_org_ids)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user_org_ids = OrganizationMembership.objects.filter(user=self.request.user).values_list(
            "organization_id", flat=True
        )
        form.fields["incident"].queryset = (
            Incident.objects.filter(project__organization_id__in=user_org_ids)
            .select_related("project", "project__organization")
            .order_by("-created_at")
        )
        return form

    def form_valid(self, form):
        messages.success(self.request, f'Postmortem "{form.instance.title}" updated successfully!')
        return super().form_valid(form)


class PostmortemDeleteView(LoginRequiredMixin, DeleteView):
    model = Postmortem
    template_name = "postmortems/delete.html"
    success_url = reverse_lazy("postmortem_list")

    def get_queryset(self):
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
        ).values_list("organization_id", flat=True)
        return Postmortem.objects.filter(incident__project__organization_id__in=user_org_ids)

    def delete(self, request, *args, **kwargs):
        postmortem = self.get_object()
        messages.success(request, f'Postmortem "{postmortem.title}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def postmortem_trigger_ingestion(request, pk):
    postmortem = get_object_or_404(Postmortem, pk=pk)
    user_org_ids = OrganizationMembership.objects.filter(
        user=request.user,
        role__in=[
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.ADMIN,
            OrganizationMembership.Role.ENGINEER,
        ],
    ).values_list("organization_id", flat=True)

    if postmortem.incident.project.organization_id not in user_org_ids:
        messages.error(request, "You do not have permission to trigger ingestion.")
        return redirect("postmortem_detail", pk=pk)

    if request.method == "POST":
        postmortem.ingestion_status = Postmortem.IngestionStatus.PROCESSING
        postmortem.processing_status = Postmortem.IngestionStatus.PROCESSING
        postmortem.embedding_status = Postmortem.IngestionStatus.PROCESSING
        postmortem.graph_indexing_status = Postmortem.IngestionStatus.PROCESSING
        postmortem.save()

        org_id = postmortem.incident.project.organization_id
        project_id = postmortem.incident.project_id
        content = json.dumps(
            {
                "title": postmortem.title,
                "document_source": postmortem.document_source,
                "content_metadata": postmortem.content_metadata,
            }
        )

        try:
            response = async_to_sync(get_fastapi_client().trigger_postmortem_ingestion)(
                title=postmortem.title,
                content=content,
                organization_id=str(org_id),
                project_id=str(project_id),
            )
        except Exception as e:
            logger.exception("Postmortem ingestion failed (transport error)")
            postmortem.ingestion_status = Postmortem.IngestionStatus.FAILED
            postmortem.processing_status = Postmortem.IngestionStatus.FAILED
            postmortem.save()
            messages.error(request, f"Ingestion failed: {e}")
            return redirect("postmortem_detail", pk=pk)

        if 200 <= response.status_code < 300:
            data = response.json() if response.content else {}
            postmortem.ingestion_status = Postmortem.IngestionStatus.COMPLETED
            postmortem.processing_status = Postmortem.IngestionStatus.COMPLETED
            postmortem.embedding_status = Postmortem.IngestionStatus.COMPLETED
            postmortem.graph_indexing_status = Postmortem.IngestionStatus.COMPLETED
            postmortem.save()
            messages.success(
                request,
                f"Postmortem ingested successfully "
                f"({data.get('chunks_created', '?')} chunks created)!",
            )
        else:
            logger.error(
                f"Postmortem ingestion failed: HTTP {response.status_code} - {response.text[:300]}"
            )
            postmortem.ingestion_status = Postmortem.IngestionStatus.FAILED
            postmortem.processing_status = Postmortem.IngestionStatus.FAILED
            postmortem.save()
            messages.error(
                request,
                f"Ingestion failed (HTTP {response.status_code}): {response.text[:200]}",
            )

        return redirect("postmortem_detail", pk=pk)

    return render(request, "postmortems/trigger_ingestion.html", {"postmortem": postmortem})


postmortem_list = PostmortemListView.as_view()
postmortem_create = PostmortemCreateView.as_view()
postmortem_detail = PostmortemDetailView.as_view()
postmortem_update = PostmortemUpdateView.as_view()
postmortem_delete = PostmortemDeleteView.as_view()
postmortem_trigger_ingestion = postmortem_trigger_ingestion
