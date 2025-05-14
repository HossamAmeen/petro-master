from django.db.models import Count
from django.db.models.base import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.views import Response

from apps.shared.base_exception_class import CustomValidationError
from apps.stations.filters import ServiceFilter, StationBranchFilter
from apps.stations.models.stations_models import Service, Station, StationBranch
from apps.stations.v1.serializers import (
    ListServiceSerializer,
    ListStationBranchSerializer,
    ListStationSerializer,
    UpdateStationBranchBalanceSerializer,
)
from apps.users.models import User


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.prefetch_related("station_services").order_by("-id")
    serializer_class = ListStationSerializer


class StationBranchViewSet(viewsets.ModelViewSet):
    queryset = (
        StationBranch.objects.prefetch_related("station_branch_services")
        .annotate(
            managers_count=Count("managers", distinct=True),
        )
        .order_by("-id")
    )
    serializer_class = ListStationBranchSerializer
    filterset_class = StationBranchFilter

    # def get_permissions(self):
    #     if self.action == "update_balance":
    #         return [StationOwnerPermission()]
    #     return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "update_balance":
            return UpdateStationBranchBalanceSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(station__owners=self.request.user)
        if self.request.user.role == User.UserRoles.StationBranchManager:
            return self.queryset.filter(station__managers__user=self.request.user)
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
                else:
                    raise CustomValidationError(
                        message="الفرع لا يمتلك كافٍ من المال",
                        code="not_enough_balance",
                        errors=[],
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
        return Response({"balance": station_branch.balance})


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by("-id")
    serializer_class = ListServiceSerializer
    filterset_class = ServiceFilter

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(
                station_branch_services__station_branch__station__owners=self.request.user
            )
        if self.request.user.role == User.UserRoles.StationBranchManager:
            return self.queryset.filter(
                station_branch_services__station_branch__station__managers__user=self.request.user
            )
        return self.queryset.distinct()
