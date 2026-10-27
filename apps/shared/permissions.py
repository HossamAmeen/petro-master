from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.shared.constants import COMPANY_ROLES, DASHBOARD_ROLES, STATION_ROLES
from apps.users.models import User


class CompanyPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in COMPANY_ROLES


class CompanyOwnerPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.UserRoles.CompanyOwner


class CompanyBranchManagerPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.UserRoles.CompanyBranchManager


class StationOwnerPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.UserRoles.StationOwner


class StationBranchManagerPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.UserRoles.StationBranchManager


class StationWorkerPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.UserRoles.StationWorker


class StationPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in STATION_ROLES


class CompanyOrDashboardPermission(BasePermission):
    """Company roles and dashboard roles only; every other role is refused."""

    def has_permission(self, request, view):
        return (
            request.user.role in COMPANY_ROLES or request.user.role in DASHBOARD_ROLES
        )


class DashboardPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in DASHBOARD_ROLES


READ_ONLY_DASHBOARD_ROLES = [
    User.UserRoles.CustomerSupport,
    User.UserRoles.Finance,
]


class CustomerSupportReadOnlyPermission(BasePermission):
    """Customer support and finance may only read; every other role is left to
    the permissions next to this one. Finance's write access to the company and
    station transactions comes from `KhaznaTransactionWritePermission`."""

    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS
            or request.user.role not in READ_ONLY_DASHBOARD_ROLES
        )


class KhaznaTransactionWritePermission(BasePermission):
    """Write rules for the company/station transaction viewsets: customer
    support only reads, finance may create and PATCH but never delete or PUT,
    and every other role is left to the permissions next to this one."""

    FINANCE_METHODS = ("POST", "PATCH")

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user.role == User.UserRoles.CustomerSupport:
            return False
        if request.user.role == User.UserRoles.Finance:
            return request.method in self.FINANCE_METHODS
        return True


class AdminPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.UserRoles.Admin


class EitherPermission(BasePermission):
    def __init__(self, permissions):
        self.permissions = permissions

    def has_permission(self, request, view):
        return any(perm().has_permission(request, view) for perm in self.permissions)
