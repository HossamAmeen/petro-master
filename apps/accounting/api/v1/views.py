from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.accounting.api.v1.filters import StationKhaznaTransactionFilter
from apps.accounting.api.v1.serializers.company_transaction_serializer import (
    KhaznaTransactionSerializer,
    ListCompanyKhaznaTransactionSerializer,
    ListStationKhaznaTransactionSerializer,
)
from apps.accounting.models import (
    CompanyKhaznaTransaction,
    KhaznaTransaction,
    StationKhaznaTransaction,
)
from apps.shared.permissions import StationPermission
from apps.users.models import User


class KhaznaTransactionViewSet(viewsets.ModelViewSet):
    queryset = KhaznaTransaction.objects.order_by("-id")
    serializer_class = KhaznaTransactionSerializer
    permission_classes = [IsAuthenticated]


class CompanyKhaznaTransactionViewSet(viewsets.ModelViewSet):
    queryset = CompanyKhaznaTransaction.objects.order_by("-id")
    serializer_class = ListCompanyKhaznaTransactionSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company=self.request.company_id)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(company=self.request.company_id)
        return self.queryset


class StationKhaznaTransactionViewSet(viewsets.ModelViewSet):
    queryset = StationKhaznaTransaction.objects.select_related(
        "station_branch__district__city"
    ).order_by("-id")
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = StationKhaznaTransactionFilter
    search_fields = ["station__name"]
    serializer_class = ListStationKhaznaTransactionSerializer
    permission_classes = [IsAuthenticated, StationPermission]

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(station_id=self.request.station_id)
        if self.request.user.role == User.UserRoles.StationBranchManager:
            return self.queryset.filter(
                station__branches__managers__user=self.request.user
            )
        return self.queryset
