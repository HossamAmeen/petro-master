from rest_framework import viewsets

from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.users.models import CompanyUser, User
from apps.users.v1.filters import CompanyBranchManagerFilter
from apps.users.v1.serializers.company_user_serializer import (
    CompanyBranchManagerSerializer,
    ListCompanyBranchManagerSerializer,
)


class CompanyBranchManagerViewSet(InjectUserMixin, viewsets.ModelViewSet):
    filterset_class = CompanyBranchManagerFilter
    queryset = (
        CompanyUser.objects.filter(role=User.UserRoles.CompanyBranchManager)
        .select_related("created_by", "updated_by")
        .order_by("-id")
    )

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            self.queryset = self.queryset.filter(company=self.request.company_id)
        return self.queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return ListCompanyBranchManagerSerializer
        return CompanyBranchManagerSerializer
