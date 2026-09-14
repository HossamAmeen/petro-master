from types import SimpleNamespace

import pytest

from apps.shared.permissions import (
    AdminPermission,
    CompanyBranchManagerPermission,
    CompanyOwnerPermission,
    CompanyPermission,
    DashboardPermission,
    EitherPermission,
    StationBranchManagerPermission,
    StationOwnerPermission,
    StationPermission,
    StationWorkerPermission,
)
from apps.users.models import User

Roles = User.UserRoles


def request_for(role):
    return SimpleNamespace(user=SimpleNamespace(role=role))


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
