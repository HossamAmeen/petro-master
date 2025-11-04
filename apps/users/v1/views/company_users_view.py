from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.shared.permissions import (
    CompanyPermission,
    DashboardPermission,
    EitherPermission,
)
from apps.users.models import CompanyUser, User
from apps.users.v1.filters import CompanyBranchManagerFilter
from apps.users.v1.serializers.company_user_serializer import (
    CompanyBranchManagerSerializer,
    CreateCompanyOwnerSerializer,
    ListCompanyBranchManagerSerializer,
    ListCompanyOwnerSerializer,
    RetrieveCompanyBranchManagerSerializer,
)


class CompanyOwnerViewSet(viewsets.ModelViewSet):
    queryset = (
        CompanyUser.objects.filter(role=User.UserRoles.CompanyOwner)
        .select_related("created_by", "updated_by")
        .order_by("-id")
    )

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListCompanyOwnerSerializer
        return CreateCompanyOwnerSerializer

    def get_permissions(self):
        return [
            IsAuthenticated(),
            EitherPermission([DashboardPermission]),
        ]


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
        if self.action == "retrieve":
            self.queryset = self.queryset.prefetch_related("company_branch_managers")
        return self.queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return ListCompanyBranchManagerSerializer
        if self.action == "create":
            return CreateCompanyOwnerSerializer
        if self.action == "retrieve":
            return RetrieveCompanyBranchManagerSerializer
        return CompanyBranchManagerSerializer

    def get_permissions(self):
        return [
            IsAuthenticated(),
            EitherPermission([CompanyPermission, DashboardPermission]),
        ]
