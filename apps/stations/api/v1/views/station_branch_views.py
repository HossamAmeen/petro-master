from django.db.models import Count
from django.db.models.base import transaction
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import Response

from apps.accounting.helpers import generate_station_transaction
from apps.accounting.models import StationKhaznaTransaction
from apps.notifications.models import Notification
from apps.shared.base_exception_class import CustomValidationError
from apps.shared.constants import DASHBOARD_ROLES
from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.shared.permissions import DashboardPermission, StationOwnerPermission
from apps.stations.api.station_serializers.station_branch_serializers import (
    StationBranchCreationSerializer,
    StationBranchUpdateSerializer,
)
from apps.stations.api.v1.serializers import (
    AssignServicesSerializer,
    ListServiceSerializer,
    ListStationBranchForLandingpageSerializer,
    ListStationBranchSerializer,
    StationBranchAssignManagersSerializer,
    UpdateStationBranchBalanceSerializer,
)
from apps.stations.filters import StationBranchFilter
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import StationBranch, StationBranchService
from apps.users.models import StationBranchManager, User

SERVICE_CATEGORY_CHOICES = {
    "petrol": [Service.ServiceType.PETROL, Service.ServiceType.DIESEL],
    "other": [Service.ServiceType.OTHER, Service.ServiceType.WASH],
}


class StationBranchViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = (
        StationBranch.objects.prefetch_related("station_branch_services", "managers")
        .annotate(
            managers_count=Count("managers", distinct=True),
        )
        .order_by("-id")
    )
    serializer_class = ListStationBranchSerializer
    filterset_class = StationBranchFilter

    def get_permissions(self):
        if self.action == "list":
            return [AllowAny()]
        if self.action == "create":
            return [IsAuthenticated(), DashboardPermission()]
        if self.action == "update_balance":
            return [IsAuthenticated(), StationOwnerPermission()]
        return super().get_permissions()

    def get_serializer_class(self):
        if not self.request.user.is_authenticated:
            return ListStationBranchForLandingpageSerializer
        if self.action == "update_balance":
            return UpdateStationBranchBalanceSerializer
        elif self.action == "services":
            return ListServiceSerializer
        elif self.action == "available_services":
            return ListServiceSerializer
        elif self.action == "assign_services":
            return AssignServicesSerializer
        elif self.action == "add_service":
            return AssignServicesSerializer
        elif self.action == "delete_service":
            return AssignServicesSerializer
        elif self.action == "assign_managers":
            return StationBranchAssignManagersSerializer
        elif self.action == "partial_update":
            return StationBranchUpdateSerializer
        elif self.action == "create":
            return StationBranchCreationSerializer
        elif self.action == "list":
            return ListStationBranchSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return self.queryset.distinct()
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(station__owners=self.request.user)
        if self.request.user.role == User.UserRoles.StationBranchManager:
            return self.queryset.filter(managers__user=self.request.user)
        if self.request.user.role in DASHBOARD_ROLES:
            return self.queryset.annotate(
                services_count=Count("station_branch_services", distinct=True),
                managers_count=Count("managers", distinct=True),
                workers_count=Count("workers", distinct=True),
            )
        return self.queryset.distinct()

    @action(detail=True, methods=["post"], url_path="update-balance")
    def update_balance(self, request, *args, **kwargs):
        station_branch = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            station = station_branch.station
            if serializer.validated_data["type"] == "add":
                station.refresh_from_db()
                if station.balance >= serializer.validated_data["amount"]:
                    station_branch.balance += serializer.validated_data["amount"]
                    station_branch.save()

                    station.balance -= serializer.validated_data["amount"]
                    station.save()
                    message = f"تم شحن رصيد فرع {station_branch.name} برصيد {serializer.validated_data['amount']}"
                    generate_station_transaction(
                        station_id=station_branch.station_id,
                        station_branch_id=station_branch.id,
                        amount=serializer.validated_data["amount"],
                        status=StationKhaznaTransaction.TransactionStatus.APPROVED,
                        description=message,
                        is_internal=True,
                        created_by_id=request.user.id,
                    )
                    notification_users = list(
                        station_branch.managers.values_list("user_id", flat=True)
                    )
                    notification_users.append(request.user.id)
                    for user_id in notification_users:
                        Notification.objects.create(
                            user_id=user_id,
                            title=message,
                            description=message,
                            type=Notification.NotificationType.MONEY,
                        )
                else:
                    raise CustomValidationError(
                        message="المحطة لا تمتلك كافٍ من المال",
                        code="not_enough_balance",
                        errors=[],
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                if station_branch.balance >= serializer.validated_data["amount"]:
                    station_branch.balance -= serializer.validated_data["amount"]
                    station_branch.save()

                    station.refresh_from_db()
                    station.balance += serializer.validated_data["amount"]
                    station.save()

                    message = f"تم خصم رصيد فرع {station_branch.name} برصيد {serializer.validated_data['amount']}"
                    generate_station_transaction(
                        station_id=station_branch.station_id,
                        amount=serializer.validated_data["amount"],
                        status=StationKhaznaTransaction.TransactionStatus.APPROVED,
                        description=message,
                        is_internal=True,
                        created_by_id=request.user.id,
                    )
                    notification_users = list(
                        station_branch.managers.values_list("user_id", flat=True)
                    )
                    notification_users.append(request.user.id)
                    for user_id in notification_users:
                        Notification.objects.create(
                            user_id=user_id,
                            title=message,
                            description=message,
                            type=Notification.NotificationType.MONEY,
                        )
                else:
                    raise CustomValidationError(
                        message="الفرع لا يمتلك كافٍ من المال",
                        code="not_enough_balance",
                        errors=[],
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
        return Response({"balance": station_branch.balance})

    @extend_schema(
        description="show station branch services",
        parameters=[
            OpenApiParameter(
                name="types",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by type exampe types=petrol,diesel,wash,other",
            ),
            OpenApiParameter(
                name="service_category",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by service category exampe service_category=petrol,other",
            ),
        ],
    )
    @action(detail=True, methods=["GET"], url_path="services")
    def services(self, request, pk=None, *args, **kwargs):
        services = Service.objects.order_by("-id")
        if self.request.user.role == User.UserRoles.StationOwner:
            services = services.filter(station_branch_services__station_branch_id=pk)
        if self.request.user.role == User.UserRoles.StationBranchManager:
            services = services.filter(
                station_branch_services__station_branch__managers__user=self.request.user,
                station_branch_services__station_branch_id=pk,
            )
        if request.query_params.get("types"):
            types = request.query_params.get("types").split(",")
            services = services.filter(type__in=types)
        if request.query_params.get("search"):
            search = request.query_params.get("search")
            services = services.filter(name__icontains=search)
        if request.query_params.get("service_category"):
            service_category = request.query_params.get("service_category")
            services = services.filter(
                type__in=SERVICE_CATEGORY_CHOICES.get(service_category)
            )
        services = services.distinct()
        page = self.paginate_queryset(services)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        description="show available station branch services to choose from them to assign to station branch",
        parameters=[
            OpenApiParameter(
                name="service_category",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by service category exampe service_category=petrol,other",
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="search by name",
            ),
        ],
    )
    @action(detail=True, methods=["GET"], url_path="available-services")
    def available_services(self, request, pk=None, *args, **kwargs):
        services = Service.objects.order_by("-id").exclude(
            station_branch_services__station_branch_id=pk
        )
        if request.query_params.get("service_category"):
            service_category = request.query_params.get("service_category")
            services = services.filter(
                type__in=SERVICE_CATEGORY_CHOICES.get(service_category)
            )
        if request.query_params.get("search"):
            search = request.query_params.get("search")
            services = services.filter(name__icontains=search)
        services = services.distinct()
        page = self.paginate_queryset(services)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        description="assign services to station branch",
        request=AssignServicesSerializer,
    )
    @action(detail=True, methods=["POST"], url_path="assign-services")
    def assign_services(self, request, *args, **kwargs):
        station_branch = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services = serializer.validated_data.get("services", [])
        station_branch.station_branch_services.all().delete()
        services = set(services)
        for service in services:
            StationBranchService.objects.create(
                station_branch=station_branch,
                service_id=service,
                created_by=self.request.user,
                updated_by=self.request.user,
            )
        return Response({"message": "تم تعيين الخدمات بنجاح"})

    @action(detail=True, methods=["POST"], url_path="assign-managers")
    def assign_managers(self, request, *args, **kwargs):
        station_branch = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        managers = serializer.validated_data.get("managers", [])
        station_branch.managers.all().delete()
        managers = set(managers)
        for manager in managers:
            StationBranchManager.objects.create(
                station_branch=station_branch,
                user_id=manager,
                created_by=self.request.user,
                updated_by=self.request.user,
            )
        return Response({"message": "تم تعيين المديرين بنجاح"})

    @extend_schema(
        description="add service to station branch",
        request=AssignServicesSerializer,
    )
    @action(detail=True, methods=["POST"], url_path="add-service")
    def add_service(self, request, *args, **kwargs):
        station_branch = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services = serializer.validated_data.get("services", None)
        if station_branch.station_branch_services.filter(
            service_id__in=services,
        ).exists():
            raise CustomValidationError(
                message="بعض الخدمة موجودة بالفعل",
                code="service_exists",
                errors=[],
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        StationBranchService.objects.bulk_create(
            [
                StationBranchService(
                    station_branch=station_branch,
                    service_id=service,
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )
                for service in services
            ]
        )
        return Response({"message": "تم إضافة الخدمة بنجاح"})

    @extend_schema(
        description="delete service to station branch",
        request=AssignServicesSerializer,
    )
    @action(detail=True, methods=["POST"], url_path="delete-service")
    def delete_service(self, request, *args, **kwargs):
        station_branch = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services = serializer.validated_data.get("services", None)
        if services:
            StationBranchService.objects.filter(
                station_branch=station_branch,
                service_id__in=services,
            ).delete()
        return Response({"message": "تم إزالة الخدمة بنجاح"})
