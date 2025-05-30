from rest_framework.permissions import BasePermission
from rest_framework.views import PermissionDenied

from apps.shared.constants import COMPANY_ROLES, STATION_ROLES
from apps.users.models import User


class CashRequestPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "DELETE"]:
            return request.user.role in COMPANY_ROLES
        if request.method == "PATCH":
            return request.user.role in STATION_ROLES
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.UserRoles.CompanyOwner:
            return True
        if request.user.role == User.UserRoles.CompanyBranchManager:
            if obj.created_by != request.user:
                raise PermissionDenied(
                    "انت لا تمتلك صلاحية الغاء هذا الطلب لانه تم انشاءه بواسطة "
                    + obj.created_by.name
                )
            return True
        return False
