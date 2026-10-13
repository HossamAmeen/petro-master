from types import SimpleNamespace

import pytest

from apps.shared.permissions import (
    AdminPermission,
    CompanyBranchManagerPermission,
    CompanyOwnerPermission,
    CompanyPermission,
    CustomerSupportReadOnlyPermission,
    DashboardPermission,
    EitherPermission,
    StationBranchManagerPermission,
    StationOwnerPermission,
    StationPermission,
    StationWorkerPermission,
)
from apps.users.models import User

Roles = User.UserRoles


def request_for(role, method="GET"):
    return SimpleNamespace(method=method, user=SimpleNamespace(role=role))


@pytest.mark.parametrize(
    "permission, allowed_role, denied_role",
    [
        (CompanyPermission, Roles.CompanyBranchManager, Roles.StationOwner),
        (CompanyOwnerPermission, Roles.CompanyOwner, Roles.CompanyBranchManager),
        (
            CompanyBranchManagerPermission,
            Roles.CompanyBranchManager,
            Roles.CompanyOwner,
        ),
        (StationOwnerPermission, Roles.StationOwner, Roles.StationWorker),
        (
            StationBranchManagerPermission,
            Roles.StationBranchManager,
            Roles.StationOwner,
        ),
        (StationWorkerPermission, Roles.StationWorker, Roles.StationOwner),
        (StationPermission, Roles.StationWorker, Roles.CompanyOwner),
        (DashboardPermission, Roles.Admin, Roles.CompanyOwner),
        (AdminPermission, Roles.Admin, Roles.Finance),
    ],
)
def test_role_permission_allows_only_matching_roles(
    permission, allowed_role, denied_role
):
    assert permission().has_permission(request_for(allowed_role), None) is True
    assert permission().has_permission(request_for(denied_role), None) is False


def test_either_permission_allows_when_any_permission_matches():
    permission = EitherPermission([CompanyOwnerPermission, StationOwnerPermission])

    assert permission.has_permission(request_for(Roles.StationOwner), None) is True
    assert permission.has_permission(request_for(Roles.Admin), None) is False


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
def test_customer_support_read_only_allows_reads(method):
    request = request_for(Roles.CustomerSupport, method)

    assert CustomerSupportReadOnlyPermission().has_permission(request, None) is True


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_customer_support_read_only_blocks_customer_support_writes(method):
    request = request_for(Roles.CustomerSupport, method)

    assert CustomerSupportReadOnlyPermission().has_permission(request, None) is False


@pytest.mark.parametrize("role", [Roles.Admin, Roles.Finance, Roles.CompanyOwner])
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_customer_support_read_only_leaves_other_roles_alone(role, method):
    request = request_for(role, method)

    assert CustomerSupportReadOnlyPermission().has_permission(request, None) is True
