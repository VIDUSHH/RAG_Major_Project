from rest_framework import permissions

from apps.api_keys.models import APIKey
from apps.organizations.models import OrganizationMembership


class IsOrganizationMember(permissions.BasePermission):
    """
    Base permission that checks if user is a member of the organization.
    Requires view.organization to be set or organization_pk in URL kwargs.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        organization = self.get_organization(view)
        if not organization:
            return False

        return OrganizationMembership.objects.filter(
            user=request.user, organization=organization
        ).exists()

    def get_organization(self, view):
        # Try to get organization from view
        org = getattr(view, "organization", None)
        if org:
            return org
        if hasattr(view, "get_organization"):
            return view.get_organization()
        # Try from URL kwargs
        org_pk = view.kwargs.get("organization_pk") or view.kwargs.get("org_pk")
        if org_pk:
            from apps.organizations.models import Organization

            try:
                return Organization.objects.get(pk=org_pk)
            except Organization.DoesNotExist:
                return None
        return None


class IsOrganizationOwner(permissions.BasePermission):
    """
    Permission check for organization owners only.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        organization = self.get_organization(view)
        if not organization:
            return False

        return OrganizationMembership.objects.filter(
            user=request.user, organization=organization, role=OrganizationMembership.Role.OWNER
        ).exists()

    def get_organization(self, view):
        org = getattr(view, "organization", None)
        if org:
            return org
        if hasattr(view, "get_organization"):
            return view.get_organization()
        org_pk = view.kwargs.get("organization_pk") or view.kwargs.get("org_pk")
        if org_pk:
            from apps.organizations.models import Organization

            try:
                return Organization.objects.get(pk=org_pk)
            except Organization.DoesNotExist:
                return None
        return None


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Permission check for organization admins and owners.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        organization = self.get_organization(view)
        if not organization:
            return False

        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=organization,
            role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
        ).exists()

    def get_organization(self, view):
        org = getattr(view, "organization", None)
        if org:
            return org
        if hasattr(view, "get_organization"):
            return view.get_organization()
        org_pk = view.kwargs.get("organization_pk") or view.kwargs.get("org_pk")
        if org_pk:
            from apps.organizations.models import Organization

            try:
                return Organization.objects.get(pk=org_pk)
            except Organization.DoesNotExist:
                return None
        return None


class IsOrganizationEngineer(permissions.BasePermission):
    """
    Permission check for engineers, admins, and owners.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        organization = self.get_organization(view)
        if not organization:
            return False

        return OrganizationMembership.objects.filter(
            user=request.user,
            organization=organization,
            role__in=[
                OrganizationMembership.Role.OWNER,
                OrganizationMembership.Role.ADMIN,
                OrganizationMembership.Role.ENGINEER,
            ],
        ).exists()

    def get_organization(self, view):
        org = getattr(view, "organization", None)
        if org:
            return org
        if hasattr(view, "get_organization"):
            return view.get_organization()
        org_pk = view.kwargs.get("organization_pk") or view.kwargs.get("org_pk")
        if org_pk:
            from apps.organizations.models import Organization

            try:
                return Organization.objects.get(pk=org_pk)
            except Organization.DoesNotExist:
                return None
        return None


class IsOrganizationViewer(permissions.BasePermission):
    """
    Permission check for any organization member (viewer and above).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        organization = self.get_organization(view)
        if not organization:
            return False

        return OrganizationMembership.objects.filter(
            user=request.user, organization=organization
        ).exists()

    def get_organization(self, view):
        org = getattr(view, "organization", None)
        if org:
            return org
        if hasattr(view, "get_organization"):
            return view.get_organization()
        org_pk = view.kwargs.get("organization_pk") or view.kwargs.get("org_pk")
        if org_pk:
            from apps.organizations.models import Organization

            try:
                return Organization.objects.get(pk=org_pk)
            except Organization.DoesNotExist:
                return None
        return None


class APIKeyScopePermission(permissions.BasePermission):
    """
    Permission that checks if the API key has required scopes.
    Requires request.auth to be an APIKey instance.
    """

    required_scopes: list[str] = []

    def has_permission(self, request, view):
        # Check if authenticated via API key
        if not hasattr(request, "auth") or not isinstance(request.auth, APIKey):
            return True  # Not an API key auth, let other permissions handle

        api_key = request.auth
        required = getattr(view, "required_scopes", self.required_scopes)

        if not required:
            return True

        return all(scope in api_key.scopes for scope in required)


def get_user_organization_queryset(user, model_class, organization_field="organization"):
    """
    Utility to filter queryset by user's organization memberships.
    Returns queryset filtered to organizations the user belongs to.
    """
    from apps.organizations.models import OrganizationMembership

    if user.is_superuser:
        return model_class.objects.all()

    org_ids = OrganizationMembership.objects.filter(user=user).values_list(
        "organization_id", flat=True
    )
    filter_kwargs = {f"{organization_field}__in": org_ids}
    return model_class.objects.filter(**filter_kwargs)


class TenantQuerysetMixin:
    """
    Mixin to automatically filter querysets by tenant (organization).
    Usage: Add to viewsets that need tenant isolation.
    """

    organization_field = "organization"

    def get_queryset(self):
        queryset = self.get_base_queryset()
        user = self.request.user

        if user.is_superuser:
            return queryset

        # Try to get organization from URL or view
        organization = None
        org = getattr(self, "organization", None)
        if org:
            organization = org
        elif hasattr(self, "get_organization"):
            organization = self.get_organization()
        else:
            org_pk = self.kwargs.get("organization_pk") or self.kwargs.get("org_pk")
            if org_pk:
                from apps.organizations.models import Organization

                try:
                    organization = Organization.objects.get(pk=org_pk)
                except Organization.DoesNotExist:
                    pass

        if organization:
            filter_kwargs = {self.organization_field: organization}
            return queryset.filter(**filter_kwargs)

        # Fallback: filter by all user's organizations
        from apps.organizations.models import OrganizationMembership

        org_ids = OrganizationMembership.objects.filter(user=user).values_list(
            "organization_id", flat=True
        )
        filter_kwargs = {f"{self.organization_field}__in": org_ids}
        return queryset.filter(**filter_kwargs)
