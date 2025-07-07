from rest_framework.permissions import BasePermission

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


class DashboardPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in DASHBOARD_ROLES
