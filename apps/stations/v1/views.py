from django.db.models import Count
from rest_framework import viewsets

from apps.stations.filters import ServiceFilter, StationBranchFilter
from apps.stations.models.stations_models import Service, Station, StationBranch
from apps.stations.v1.serializers import (
    ListServiceSerializer,
    ListStationBranchSerializer,
    ListStationSerializer,
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

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(station__owners=self.request.user)
        if self.request.user.role == User.UserRoles.StationBranchManager:
            return self.queryset.filter(station__managers__user=self.request.user)
        return self.queryset.distinct()


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
