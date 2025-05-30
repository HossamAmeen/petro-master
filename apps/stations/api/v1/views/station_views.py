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
from rest_framework.views import APIView, Response

from apps.companies.api.v1.filters import CarOperationFilter
from apps.companies.api.v1.serializers.car_operation_serializer import (
    ListCarOperationSerializer,
    ListStationCarOperationSerializer,
)
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.operation_model import CarOperation
from apps.stations.api.station_serializers.home_serializers import (
    ListStationReportsSerializer,
)
from apps.stations.api.v1.serializers import ListStationSerializer
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import User


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.prefetch_related("station_services").order_by("-id")
    serializer_class = ListStationSerializer


class StationHomeAPIView(APIView):
    def get(self, request):
        if request.user.role == User.UserRoles.StationOwner:
            station_branches_id = StationBranch.objects.filter(
                station_id=request.station_id
            ).values_list("id", flat=True)

        if request.user.role == User.UserRoles.StationBranchManager:
            station_branches_id = StationBranch.objects.filter(
                managers__user=request.user
            ).values_list("id", flat=True)

        branches_filter = Q(branches__id__in=list(station_branches_id))

        station = (
            Station.objects.filter(id=request.station_id)
            .annotate(
                workers_count=Count(
                    "branches__workers", distinct=True, filter=branches_filter
                ),
                managers_count=Count(
                    "branches__managers", distinct=True, filter=branches_filter
                ),
                branches_count=Count("branches", distinct=True, filter=branches_filter),
            )
            .first()
        )

        if request.user.role == User.UserRoles.StationOwner:
            base_balance = station.balance

            branches_balance = (
                StationBranch.objects.filter(station_id=request.station_id)
                .aggregate(balance=Sum("balance"))
                .get("balance")
            )

            distributed_balance = branches_balance

        if request.user.role == User.UserRoles.StationBranchManager:
            branches_balance = (
                StationBranch.objects.filter(managers__user=request.user)
                .aggregate(balance=Sum("balance"))
                .get("balance")
            )

            base_balance = branches_balance

            distributed_balance = branches_balance

        last_operations = CarOperation.objects.filter(
            station_branch__station_id__in=station_branches_id
        ).order_by("-id")[:5]

        response_data = {
            "id": station.id,
            "name": station.name,
            "address": station.address,
            "balance": base_balance,
            "branches_balance": branches_balance,
            "distributed_balance": distributed_balance,
            "total_balance": base_balance + distributed_balance,
            "workers_count": station.workers_count,
            "managers_count": station.managers_count,
            "branches_count": station.branches_count,
            "last_operations": ListCarOperationSerializer(
                last_operations, many=True
            ).data,
        }
        return Response(response_data)


class StationOperationsAPIView(ListAPIView):
    queryset = CarOperation.objects.select_related(
        "car", "driver", "station_branch", "worker", "service"
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
        if request.user.role == User.UserRoles.StationBranchManager:
            station_branch_filter = Q(station_branch__managers__user=request.user)

        today = date.today()
        date_from = request.query_params.get("date_from", today)
        date_to = request.query_params.get("date_to", None)
        if date_from:
            station_branch_filter &= Q(modified__date__gte=date_from)
        if date_to:
            station_branch_filter &= Q(modified__date__lte=date_to)

        operations = (
            CarOperation.objects.filter(station_branch_filter)
            .select_related("service")
            .values("service")
            .annotate(
                total_balance=Sum("cost"),
                count=Count("id"),
                amount=Sum("amount"),
                service_name=F("service__name"),
                unit=F("service__unit"),
            )
            .order_by("-total_balance")
        )
        operations = ListStationReportsSerializer(operations, many=True).data

        cash_request_balance_balance = (
            CompanyCashRequest.objects.filter(
                station_branch_filter,
                status=CompanyCashRequest.Status.APPROVED,
            ).aggregate(total_balance=Sum("amount"))["total_balance"]
            or 0
        )

        response_data = {
            "station_branch_filter": station_branch_filter,
            "station_id": request.station_id,
            "cash_request_balance": cash_request_balance_balance,
            "operations": operations,
        }
        return Response(response_data)
