from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import Response, status

from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.v1.serializers.company_cash_request_serializers import (
    CompanyCashRequestSerializer,
    ListCompanyCashRequestSerializer,
)
from apps.shared.mixins.inject_user_mixins import InjectCompanyUserMixin
from apps.shared.permissions import CompanyPermission
from apps.users.models import User


class CompanyCashRequestViewSet(InjectCompanyUserMixin, viewsets.ModelViewSet):
    queryset = CompanyCashRequest.objects.select_related("driver", "station").order_by(
        "-id"
    )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [CompanyPermission()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListCompanyCashRequestSerializer
        return CompanyCashRequestSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company=self.request.company_id)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(branch__managers__user=self.request.user)
        return self.queryset

    def destroy(self, request, *args, **kwargs):
        item = self.get_object()
        if item.status == CompanyCashRequest.Status.IN_PROGRESS:
            item.status = CompanyCashRequest.Status.REJECTED
            item.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)
