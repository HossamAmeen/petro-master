from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.accounting.api.v1.filters import (
    CompanyKhaznaTransactionFilter,
    StationKhaznaTransactionFilter,
)
from apps.accounting.api.v1.serializers.company_transaction_serializer import (
    CreateCompanyKhaznaTransactionSerializer,
    CreateStationKhaznaTransactionSerializer,
    KhaznaTransactionSerializer,
    ListCompanyKhaznaTransactionForDashboardSerializer,
    ListCompanyKhaznaTransactionSerializer,
    ListStationKhaznaTransactionSerializer,
)
from apps.accounting.models import (
    CompanyKhaznaTransaction,
    KhaznaTransaction,
    StationKhaznaTransaction,
)
from apps.shared.constants import COMPANY_ROLES, DASHBOARD_ROLES
from apps.shared.permissions import (
    CompanyPermission,
    DashboardPermission,
    EitherPermission,
    StationPermission,
)
from apps.users.models import User


class KhaznaTransactionViewSet(viewsets.ModelViewSet):
    queryset = KhaznaTransaction.objects.order_by("-id")
    serializer_class = KhaznaTransactionSerializer
    permission_classes = [IsAuthenticated]


class CompanyKhaznaTransactionViewSet(viewsets.ModelViewSet):
    queryset = CompanyKhaznaTransaction.objects.order_by("-id")
    serializer_class = ListCompanyKhaznaTransactionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["company__name"]
    filterset_class = CompanyKhaznaTransactionFilter

    def get_permissions(self):
        return [
            IsAuthenticated(),
            EitherPermission([CompanyPermission, DashboardPermission]),
        ]

    def get_serializer_class(self):
        if self.action == "list":
            if self.request.user.role in COMPANY_ROLES:
                return ListCompanyKhaznaTransactionSerializer
            if self.request.user.role in DASHBOARD_ROLES:
                return ListCompanyKhaznaTransactionForDashboardSerializer
        return CreateCompanyKhaznaTransactionSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company=self.request.company_id)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(company=self.request.company_id)
        return self.queryset


class StationKhaznaTransactionViewSet(viewsets.ModelViewSet):
    queryset = StationKhaznaTransaction.objects.order_by("-id")
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = StationKhaznaTransactionFilter
    search_fields = ["station__name"]
    filter_fields = [
        "station",
        "station_branch",
        "is_incoming",
        "method",
        "is_internal",
    ]
    serializer_class = ListStationKhaznaTransactionSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return ListStationKhaznaTransactionSerializer
        return CreateStationKhaznaTransactionSerializer

    def get_permissions(self):
        return [
            IsAuthenticated(),
            EitherPermission([StationPermission, DashboardPermission]),
        ]

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(station_id=self.request.station_id)
        if self.request.user.role == User.UserRoles.StationBranchManager:
            return self.queryset.filter(
                station__branches__managers__user=self.request.user
            )
        return self.queryset
