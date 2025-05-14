from rest_framework.permissions import BasePermission

from apps.users.models import User


class CompanyPermission(BasePermission):
    def has_permission(self, request, view):
        if (
            request.user.role == User.UserRoles.CompanyOwner
            or request.user.role == User.UserRoles.CompanyBranchManager
        ):
            return True
        return False


class CompanyOwnerPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == User.UserRoles.CompanyOwner:
            return True
        return False


class CompanyBranchManagerPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == User.UserRoles.CompanyBranchManager:
            return True
        return False


class StationOwnerPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == User.UserRoles.StationOwner:
            return True
        return False


class StationBranchManagerPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == User.UserRoles.StationBranchManager:
            return True
        return False


class StationPermission(BasePermission):
    def has_permission(self, request, view):
        if (
            request.user.role == User.UserRoles.StationOwner
            or request.user.role == User.UserRoles.StationBranchManager
        ):
            return True
        return False
