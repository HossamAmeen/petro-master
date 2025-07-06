from datetime import date

from django.db.models import Count, F, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView, Response

from apps.companies.api.v1.filters import CarOperationFilter
from apps.companies.api.v1.serializers.car_operation_serializer import (
    ListCarOperationSerializer,
    ListStationCarOperationSerializer,
)
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.operation_model import CarOperation
from apps.shared.permissions import StationPermission
from apps.stations.api.station_serializers.home_serializers import (
    ListStationReportsSerializer,
)
from apps.stations.api.v1.serializers import ListStationSerializer
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import StationBranchManager, StationOwner, User, Worker


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.prefetch_related("station_services").order_by("-id")
    serializer_class = ListStationSerializer


class StationHomeAPIView(APIView):
    permission_classes = [IsAuthenticated, StationPermission]

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "station_branch_id": {"type": "integer"},
                        "name": {"type": "string"},
                        "station_name": {"type": "string"},
                        "user_name": {"type": "string"},
                        "address": {"type": "string"},
                        "balance": {"type": "number"},
                        "branches_balance": {"type": "number"},
                        "distributed_balance": {"type": "number"},
                        "total_balance": {"type": "number"},
                        "workers_count": {"type": "integer"},
                        "managers_count": {"type": "integer"},
                        "branches_count": {"type": "integer"},
                        "last_operations": {"type": "array", "items": "object"},
                    },
                }
            )
        }
    )
    def get(self, request):
        operation_filter = Q()
        manager_count = 0
        branch_count = 0
        workers_count = 0
        if request.user.role == User.UserRoles.StationOwner:
            operation_filter = Q(station_branch__station_id=request.station_id)
            manager_count = StationOwner.objects.filter(
                station_id=request.station_id, role=User.UserRoles.StationBranchManager
            ).count()
            branch_count = StationBranch.objects.filter(
                station_id=request.station_id
            ).count()
            workers_count = Worker.objects.filter(
                station_branch__station_id=request.station_id
            ).count()
        if request.user.role == User.UserRoles.StationBranchManager:
            branches_list = list(
                StationBranchManager.objects.filter(user=request.user).values_list(
                    "station_branch_id", flat=True
                )
            )
            manager_count = (
                StationBranchManager.objects.filter(station_branch__in=branches_list)
                .exclude(user=request.user)
                .count()
            )
            branch_count = len(branches_list)
            workers_count = Worker.objects.filter(
                station_branch__id__in=branches_list
            ).count()
            operation_filter = Q(station_branch__in=branches_list)

        station = Station.objects.filter(id=request.station_id).first()

        if request.user.role == User.UserRoles.StationOwner:
            base_balance = station.balance

            branches_balance = (
                StationBranch.objects.filter(station_id=request.station_id)
                .aggregate(balance=Sum("balance"))
                .get("balance")
            )

            distributed_balance = branches_balance or 0

        if request.user.role == User.UserRoles.StationBranchManager:
            branches_balance = (
                StationBranch.objects.filter(managers__user=request.user)
                .aggregate(balance=Sum("balance"))
                .get("balance")
            )

            base_balance = branches_balance or 0

            distributed_balance = branches_balance or 0
        if request.user.role == User.UserRoles.StationWorker:
            base_balance = 0
            distributed_balance = 0
            branches_balance = 0

        last_operations = (
            CarOperation.objects.select_related(
                "car", "driver", "station_branch", "worker__station_branch", "service"
            )
            .filter(operation_filter)
            .order_by("-id")[:5]
        )

        response_data = {
            "id": station.id,
            "station_branch_id": (
                request.user.worker.station_branch_id
                if request.user.role == User.UserRoles.StationWorker
                else None
            ),
            "name": station.name,
            "station_name": station.name,
            "user_name": request.user.name,
            "address": station.address,
            "balance": base_balance,
            "branches_balance": branches_balance,
            "distributed_balance": distributed_balance,
            "total_balance": base_balance + distributed_balance,
            "workers_count": workers_count,
            "managers_count": manager_count,
            "branches_count": branch_count,
            "last_operations": ListCarOperationSerializer(
                last_operations, many=True
            ).data,
        }
        return Response(response_data)


class StationOperationsAPIView(ListAPIView):
    queryset = CarOperation.objects.select_related(
        "car", "driver", "station_branch", "worker__station_branch", "service"
    ).order_by("-id")
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = CarOperationFilter
    serializer_class = ListStationCarOperationSerializer
    search_fields = [
        "code",
        "car__code",
        "driver__name",
        "station_branch__name",
        "worker__name",
    ]

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.StationOwner:
            queryset = self.queryset.filter(
                station_branch__station_id=self.request.station_id
            )
        if self.request.user.role == User.UserRoles.StationBranchManager:
            queryset = self.queryset.filter(
                station_branch__managers__user=self.request.user
            )
        if self.request.user.role == User.UserRoles.StationWorker:
            queryset = self.queryset.filter(worker=self.request.user)
        return queryset

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        petrol_service_balance = (
            queryset.filter(
                service__type__in=[
                    Service.ServiceType.PETROL,
                    Service.ServiceType.DIESEL,
                ]
            ).aggregate(total_balance=Sum("cost"))["total_balance"]
            or 0
        )
        other_service_balance = (
            queryset.filter(
                service__type__in=[Service.ServiceType.WASH, Service.ServiceType.OTHER]
            ).aggregate(total_balance=Sum("cost"))["total_balance"]
            or 0
        )
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(page, many=True)
        response = self.get_paginated_response(serializer.data)

        response.data["petrol_balance"] = petrol_service_balance
        response.data["other_balance"] = other_service_balance
        response.data["total_balance"] = petrol_service_balance + other_service_balance
        return response


class StationReportsAPIView(APIView):
    permission_classes = [IsAuthenticated, StationPermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter by date from example date_from=YYYY-MM-DD",
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter by date to example date_to=YYYY-MM-DD",
            ),
            OpenApiParameter(
                name="time_from",
                type=OpenApiTypes.TIME,
                location=OpenApiParameter.QUERY,
                description="Filter by time from example time_from=HH:MM:SS",
            ),
            OpenApiParameter(
                name="time_to",
                type=OpenApiTypes.TIME,
                location=OpenApiParameter.QUERY,
                description="Filter by time to example time_to=HH:MM:SS",
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Success",
                examples=[
                    OpenApiExample(
                        "Example response",
                        value={
                            "cash_request_balance": 100,
                            "operations": [
                                {
                                    "service": 1,
                                    "service_name": "بنزين 92",
                                    "total_balance": 100,
                                    "count": 1,
                                    "amount": 100,
                                    "unit": "لتر",
                                }
                            ],
                        },
                    )
                ],
            )
        },
    )
    def get(self, request):
        station_branch_filter = Q()
        if request.user.role == User.UserRoles.StationOwner:
            station_branch_filter = Q(station_branch__station_id=request.station_id)
            cash_request_filter = station_branch_filter
        if request.user.role == User.UserRoles.StationBranchManager:
            station_branch_filter = Q(station_branch__managers__user=request.user)
            cash_request_filter = station_branch_filter
        if request.user.role == User.UserRoles.StationWorker:
            station_branch_filter = Q(worker=request.user)
            cash_request_filter = Q(approved_by_id=request.user.id)

        today = date.today()
        date_from = request.query_params.get("date_from", today)
        date_to = request.query_params.get("date_to", None)
        time_from = request.query_params.get("time_from", "00:00:00")
        time_to = request.query_params.get("time_to", "23:59:59")
        if date_from:
            station_branch_filter &= Q(modified__date__gte=date_from)
            cash_request_filter &= Q(modified__date__gte=date_from)
        if date_to:
            station_branch_filter &= Q(modified__date__lte=date_to)
            cash_request_filter &= Q(modified__date__lte=date_to)
        if time_from:
            station_branch_filter &= Q(modified__time__gte=time_from)
            cash_request_filter &= Q(modified__time__gte=time_from)
        if time_to:
            station_branch_filter &= Q(modified__time__lte=time_to)
            cash_request_filter &= Q(modified__time__lte=time_to)

        operations = (
            CarOperation.objects.filter(station_branch_filter)
            .select_related("service")
            .values("service")
            .annotate(
                total_balance=Sum("station_cost"),
                count=Count("id"),
                amount=Sum("amount"),
                service_name=F("service__name"),
                unit=F("service__unit"),
            )
            .order_by("-total_balance")
        )
        operations = ListStationReportsSerializer(operations, many=True).data

        cash_request_balance = (
            CompanyCashRequest.objects.filter(
                cash_request_filter,
                status=CompanyCashRequest.Status.APPROVED,
            ).aggregate(total_balance=Sum("amount"))["total_balance"]
            or 0
        )

        response_data = {
            "station_branch_filter": str(station_branch_filter),
            "station_id": request.station_id,
            "cash_request_balance": cash_request_balance,
            "operations": operations,
        }
        return Response(response_data)
