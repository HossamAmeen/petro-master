from django.db.models import F
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import viewsets
from rest_framework.views import Response, status

from apps.companies.api.filters.cash_request_filter import CashRequestFilter
from apps.companies.api.v1.permissions import CashRequestPermission
from apps.companies.api.v1.serializers.company_cash_request_serializers import (
    CompanyCashRequestSerializer,
    ListCompanyCashRequestSerializer,
)
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Company, CompanyBranch
from apps.shared.base_exception_class import CustomValidationError
from apps.shared.mixins.inject_user_mixins import InjectCompanyUserMixin
from apps.users.models import User


class CompanyCashRequestViewSet(InjectCompanyUserMixin, viewsets.ModelViewSet):
    queryset = CompanyCashRequest.objects.select_related("driver", "station").order_by(
        "-id"
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = CashRequestFilter
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        return [CashRequestPermission()]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListCompanyCashRequestSerializer
        return CompanyCashRequestSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company=self.request.company_id)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(
                driver__branch__company_id=self.request.company_id
            )
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(station__owner=self.request.station_id)
        if self.request.user.role == User.UserRoles.StationBranchManager:
            return self.queryset.filter(
                station__branches__managers__user=self.request.user
            )
        return self.queryset

    @extend_schema(
        description="List all cash requests",
        parameters=[
            OpenApiParameter(
                name="approved_by",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="when logged in as station worker must send approved_by as filter to get cash requests approved by the worker and status=APPROVED",
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        if CompanyCashRequest.objects.filter(
            driver_id=request.data["driver"],
            status=CompanyCashRequest.Status.IN_PROGRESS,
        ).exists():
            raise CustomValidationError(
                message="السائق لديه طلب بالفعل",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        if request.user.role == User.UserRoles.CompanyOwner:
            Company.objects.filter(id=request.company_id).update(
                balance=F("balance") - serializer.validated_data["amount"]
            )
        else:
            CompanyBranch.objects.select_for_update().filter(
                drivers__id=request.data["driver"]
            ).update(balance=F("balance") - serializer.validated_data["amount"])
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def destroy(self, request, *args, **kwargs):
        item = self.get_object()
        if item.status == CompanyCashRequest.Status.IN_PROGRESS:
            item.status = CompanyCashRequest.Status.REJECTED
            item.save()
            if request.user.role == User.UserRoles.CompanyOwner:
                Company.objects.filter(id=request.company_id).update(
                    balance=F("balance") + item.amount
                )
            else:
                CompanyBranch.objects.select_for_update().filter(
                    drivers__id=item.driver_id
                ).update(balance=F("balance") + item.amount)
            return Response(status=status.HTTP_204_NO_CONTENT)
        raise CustomValidationError(
            message="لا يمكنك الغاء العمليه وهيا بالحالة " + item.status,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
