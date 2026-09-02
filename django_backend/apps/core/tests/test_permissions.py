import pytest

from apps.accounts.models import User
from apps.core.permissions import (
    IsOrganizationAdmin,
    IsOrganizationEngineer,
    IsOrganizationOwner,
    IsOrganizationViewer,
    TenantQuerysetMixin,
)
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project


class MockView:
    """Simple mock view for testing permissions."""

    def __init__(self, kwargs=None, organization=None):
        self.kwargs = kwargs or {}
        self.organization = organization

    def get(self, key, default=None):
        return self.kwargs.get(key, default)


@pytest.fixture
def org_with_memberships(db):
    org = Organization.objects.create(name="Test Org", slug="test-org")
    owner = User.objects.create_user(email="owner@example.com", password="pass")
    admin = User.objects.create_user(email="admin@example.com", password="pass")
    engineer = User.objects.create_user(email="engineer@example.com", password="pass")
    viewer = User.objects.create_user(email="viewer@example.com", password="pass")
    outsider = User.objects.create_user(email="outsider@example.com", password="pass")

    OrganizationMembership.objects.create(
        user=owner, organization=org, role=OrganizationMembership.Role.OWNER
    )
    OrganizationMembership.objects.create(
        user=admin, organization=org, role=OrganizationMembership.Role.ADMIN
    )
    OrganizationMembership.objects.create(
        user=engineer, organization=org, role=OrganizationMembership.Role.ENGINEER
    )
    OrganizationMembership.objects.create(
        user=viewer, organization=org, role=OrganizationMembership.Role.VIEWER
    )

    return {
        "org": org,
        "owner": owner,
        "admin": admin,
        "engineer": engineer,
        "viewer": viewer,
        "outsider": outsider,
    }


class TestIsOrganizationOwner:
    @pytest.mark.django_db
    def test_owner_has_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["owner"]

        perm = IsOrganizationOwner()
        assert perm.has_permission(request, view) is True

    @pytest.mark.django_db
    def test_admin_no_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["admin"]

        perm = IsOrganizationOwner()
        assert perm.has_permission(request, view) is False

    @pytest.mark.django_db
    def test_non_member_no_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["outsider"]

        perm = IsOrganizationOwner()
        assert perm.has_permission(request, view) is False


class TestIsOrganizationAdmin:
    @pytest.mark.django_db
    def test_owner_has_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["owner"]

        perm = IsOrganizationAdmin()
        assert perm.has_permission(request, view) is True

    @pytest.mark.django_db
    def test_admin_has_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["admin"]

        perm = IsOrganizationAdmin()
        assert perm.has_permission(request, view) is True

    @pytest.mark.django_db
    def test_engineer_no_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["engineer"]

        perm = IsOrganizationAdmin()
        assert perm.has_permission(request, view) is False


class TestIsOrganizationEngineer:
    @pytest.mark.django_db
    def test_owner_has_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["owner"]

        perm = IsOrganizationEngineer()
        assert perm.has_permission(request, view) is True

    @pytest.mark.django_db
    def test_admin_has_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["admin"]

        perm = IsOrganizationEngineer()
        assert perm.has_permission(request, view) is True

    @pytest.mark.django_db
    def test_engineer_has_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["engineer"]

        perm = IsOrganizationEngineer()
        assert perm.has_permission(request, view) is True

    @pytest.mark.django_db
    def test_viewer_no_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["viewer"]

        perm = IsOrganizationEngineer()
        assert perm.has_permission(request, view) is False


class TestIsOrganizationViewer:
    @pytest.mark.django_db
    def test_all_roles_have_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        for user in [
            org_with_memberships["owner"],
            org_with_memberships["admin"],
            org_with_memberships["engineer"],
            org_with_memberships["viewer"],
        ]:
            request = rf.get("/")
            request.user = user

            perm = IsOrganizationViewer()
            assert perm.has_permission(request, view) is True

    @pytest.mark.django_db
    def test_outsider_no_permission(self, org_with_memberships, rf):
        view = MockView(
            kwargs={"organization_pk": str(org_with_memberships["org"].id)}, organization=None
        )

        request = rf.get("/")
        request.user = org_with_memberships["outsider"]

        perm = IsOrganizationViewer()
        assert perm.has_permission(request, view) is False


class BaseTestView:
    model = Project

    def get_base_queryset(self):
        return self.model.objects.all()

    def get_queryset(self):
        return super().get_queryset()


class TestTenantQuerysetMixin:
    @pytest.mark.django_db
    def test_filters_by_organization_from_kwargs(self, org_with_memberships, rf):
        org = org_with_memberships["org"]
        user = org_with_memberships["engineer"]

        Project.objects.create(organization=org, name="Project 1", slug="proj-1")
        Project.objects.create(organization=org, name="Project 2", slug="proj-2")

        # Create another org and project
        other_org = Organization.objects.create(name="Other Org", slug="other-org")
        Project.objects.create(organization=other_org, name="Other Project", slug="other-proj")

        class TestView(BaseTestView, TenantQuerysetMixin):
            organization_field = "organization"

            def __init__(self):
                self.request = None
                self.kwargs = {}
                self.get = lambda key, default=None: self.kwargs.get(key, default)

        view = TestView()
        view.request = rf.get("/")
        view.request.user = user
        view.kwargs = {"organization_pk": str(org.id)}

        queryset = view.get_queryset()
        assert queryset.count() == 2
        assert all(p.organization == org for p in queryset)

    @pytest.mark.django_db
    def test_superuser_sees_all(self, org_with_memberships, rf):
        org = org_with_memberships["org"]
        user = User.objects.create_superuser(email="super@example.com", password="pass")

        Project.objects.create(organization=org, name="Project 1", slug="proj-1")

        other_org = Organization.objects.create(name="Other Org", slug="other-org")
        Project.objects.create(organization=other_org, name="Other Project", slug="other-proj")

        class TestView(BaseTestView, TenantQuerysetMixin):
            organization_field = "organization"

            def __init__(self):
                self.request = None
                self.kwargs = {}
                self.get = lambda key, default=None: self.kwargs.get(key, default)

        view = TestView()
        view.request = rf.get("/")
        view.request.user = user
        view.kwargs = {}

        queryset = view.get_queryset()
        assert queryset.count() == 2
