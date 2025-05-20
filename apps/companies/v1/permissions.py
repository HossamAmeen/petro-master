from rest_framework.permissions import BasePermission

from apps.shared.constants import COMPANY_ROLES
from apps.users.models import User


class CashRequestPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in ["GET", "POST", "PATCH", "DELETE"]:
            return request.user.role in COMPANY_ROLES
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.UserRoles.CompanyOwner:
            return True
        if request.user.role == User.UserRoles.CompanyBranchManager:
            return obj.created_by == request.user
        return False
