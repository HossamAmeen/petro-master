from django.db import transaction
from django.db.models import F
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import Response, status

from apps.accounting.helpers import (
    generate_company_transaction,
    generate_station_transaction,
)
from apps.accounting.models import CompanyKhaznaTransaction, KhaznaTransaction
from apps.companies.api.filters.cash_request_filter import CashRequestFilter
from apps.companies.api.v1.permissions import CashRequestPermission
from apps.companies.api.v1.serializers.company_cash_request_serializers import (
    CompanyCashRequestSerializer,
    CompanyCashRequestUpdateSerializer,
    ListCompanyCashRequestSerializer,
)
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Company, CompanyBranch
from apps.notifications.models import Notification
from apps.shared.base_exception_class import CustomValidationError
from apps.shared.mixins.inject_user_mixins import InjectCompanyUserMixin
from apps.stations.models.stations_models import Station
from apps.users.models import (
    CompanyBranchManager,
    CompanyUser,
    StationBranchManager,
    StationOwner,
    User,
)


class CompanyCashRequestViewSet(InjectCompanyUserMixin, viewsets.ModelViewSet):
    queryset = CompanyCashRequest.objects.select_related(
        "driver", "station", "station_branch__district__city", "approved_by"
    ).order_by("-id")
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = CashRequestFilter
    search_fields = ["driver__code", "driver__name", "driver__phone_number"]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        return [IsAuthenticated(), CashRequestPermission()]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListCompanyCashRequestSerializer
        if self.request.method == "POST":
            return CompanyCashRequestSerializer
        if self.request.method == "PATCH":
            return CompanyCashRequestUpdateSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company=self.request.company_id)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(
                driver__branch__company_id=self.request.company_id
            )
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(
                station_branch__station_id=self.request.station_id
            )
        if self.request.user.role == User.UserRoles.StationBranchManager:
            return self.queryset.filter(
                station_branch__station__branches__managers__user=self.request.user
            )
        if self.request.user.role == User.UserRoles.StationWorker:
            if self.request.query_params.get("driver_code") or self.action == "PATCH":
                return self.queryset.filter(
                    status=CompanyCashRequest.Status.IN_PROGRESS,
                )
            elif self.action == "list":
                return self.queryset.filter(
                    approved_by_id=self.request.user.id,
                    status=CompanyCashRequest.Status.APPROVED,
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
            OpenApiParameter(
                name="approved_from",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="when filter by approved_from as date in format YYYY-MM-DD",
            ),
            OpenApiParameter(
                name="approved_to",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="when filter by approved_to as date in format YYYY-MM-DD",
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="when filter by status as string example status=in_progress,approved,rejected",
                enum=["in_progress", "approved", "rejected"],
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Create a new cash request",
        request=CompanyCashRequestSerializer,
        responses={
            201: OpenApiResponse(
                response=CompanyCashRequestSerializer,
                description="Cash request created successfully.",
            )
        },
    )
    @transaction.atomic
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
        cash_request = self.perform_create(serializer)

        company_branch = cash_request.driver.branch
        company_cost = (
            cash_request.amount * company_branch.cash_request_fees / 100
        ) + cash_request.amount
        company_owner_id = None
        if request.user.role == User.UserRoles.CompanyOwner:
            company_owner_id = request.user.id
            Company.objects.select_for_update().filter(id=request.company_id).update(
                balance=F("balance") - company_cost
            )
        else:
            CompanyBranch.objects.select_for_update().filter(
                drivers__id=request.data["driver"]
            ).update(balance=F("balance") - company_cost)

        cash_request.company_cost = company_cost
        cash_request.save()

        if company_owner_id:
            Notification.objects.create(
                user_id=company_owner_id,
                title=f"تم ارسال طلب نقدي الي السائق {cash_request.driver.name} ورمز التفعيل {cash_request.otp}",
                description=f"تم ارسال طلب نقدي الي السائق {cash_request.driver.name} ورمز التفعيل {cash_request.otp}",
                type=Notification.NotificationType.GENERAL,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        cash_request = CompanyCashRequest.objects.filter(id=kwargs["pk"]).first()
        if not cash_request:
            raise CustomValidationError(
                message="الطلب غير موجود", status_code=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(
            instance=cash_request, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        company_branch = cash_request.driver.branch

        station_branch = request.user.worker.station_branch
        cash_request.status = CompanyCashRequest.Status.APPROVED
        cash_request.station_branch = station_branch
        cash_request.station_id = station_branch.station_id
        cash_request.approved_by_id = request.user.id
        cash_request.save()

        # company
        message = f"تم تسليم طلب نقدي بقيمة {cash_request.company_cost:.2f} للسائق {cash_request.driver.name}"  # noqa
        generate_company_transaction(
            company_id=company_branch.company_id,
            amount=cash_request.company_cost,
            status=KhaznaTransaction.TransactionStatus.APPROVED,
            description=message,
            is_internal=False,
            for_what=CompanyKhaznaTransaction.ForWhat.DRIVER,
            created_by_id=request.user.id,
        )
        notification_users = list(
            CompanyBranchManager.objects.filter(
                company_branch_id=company_branch.id
            ).values_list("user", flat=True)
        )
        company_owner = CompanyUser.objects.filter(
            company_id=company_branch.company_id
        ).first()
        notification_users.append(company_owner.id)
        for user_id in notification_users:
            Notification.objects.create(
                user_id=user_id,
                title=message,
                description=message,
                type=Notification.NotificationType.MONEY,
            )

        # station
        station_cost = (
            cash_request.amount * station_branch.cash_request_fees / 100
        ) + cash_request.amount
        message = f"تم تسليم طلب نقدي بقيمة {station_cost:.2f} للسائق {cash_request.driver.name}"  # noqa
        generate_station_transaction(
            station_id=station_branch.station_id,
            station_branch_id=station_branch.id,
            amount=station_cost,
            status=KhaznaTransaction.TransactionStatus.APPROVED,
            description=message,
            created_by_id=request.user.id,
            is_internal=False,
        )
        notification_users = list(
            StationBranchManager.objects.filter(
                station_branch_id=station_branch.id
            ).values_list("user", flat=True)
        )
        station_owner = StationOwner.objects.filter(
            station_id=station_branch.station_id
        ).first()
        notification_users.append(station_owner.id)
        notification_users.append(request.user.id)
        notification_users = list(set(notification_users))
        for user_id in notification_users:
            Notification.objects.create(
                user_id=user_id,
                title=message,
                description=message,
                type=Notification.NotificationType.MONEY,
            )
        Station.objects.select_for_update().filter(id=cash_request.station_id).update(
            balance=F("balance") - station_cost
        )

        cash_request.station_cost = station_cost
        cash_request.save(update_fields=["station_cost"])

        return Response({"message": "تم تأكيد طلبك"})
