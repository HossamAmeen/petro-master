from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounting.models import CompanyKhaznaTransaction, KhaznaTransaction
from apps.accounting.v1.serializers.company_transaction_serializer import (
    CompanyKhaznaTransactionSerializer,
    KhaznaTransactionSerializer,
)
from apps.users.models import User


class KhaznaTransactionViewSet(viewsets.ModelViewSet):
    queryset = KhaznaTransaction.objects.all()
    serializer_class = KhaznaTransactionSerializer
    permission_classes = [IsAuthenticated]


class CompanyKhaznaTransactionViewSet(viewsets.ModelViewSet):
    queryset = CompanyKhaznaTransaction.objects.all()
    serializer_class = CompanyKhaznaTransactionSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company=self.request.company_id)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(company=self.request.company_id)
        return self.queryset
