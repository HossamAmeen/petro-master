from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from apps.users.models import StationOwner, User, Worker
from apps.users.v1.filters import StationBranchManagerFilter
from apps.users.v1.serializers.station_serializer import (
    CreateWorkerSerializer,
    ListStationBranchManagerSerializer,
    ListStationOwnerSerializer,
    ListWorkerSerializer,
    StationOwnerSerializer,
    UpdateWorkerSerializer,
)


class StationOwnerViewSet(viewsets.ModelViewSet):
    queryset = StationOwner.objects.select_related("station").order_by("-id")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["station"]
    search_fields = ["name", "phone_number", "email"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListStationOwnerSerializer
        return StationOwnerSerializer


class StationBranchManagerViewSet(viewsets.ModelViewSet):
    queryset = StationOwner.objects.filter(
        role=User.UserRoles.StationBranchManager
    ).order_by("-id")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = StationBranchManagerFilter
    search_fields = ["name", "phone_number", "email"]

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(station=self.request.station_id)
        return self.queryset

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListStationBranchManagerSerializer


class WorkerViewSet(viewsets.ModelViewSet):
    queryset = Worker.objects.select_related("station_branch").order_by("-id")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["station_branch"]
    search_fields = ["name", "phone_number", "email"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListWorkerSerializer
        if self.request.method == "POST":
            return CreateWorkerSerializer
        if self.request.method == "PATCH":
            return UpdateWorkerSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(
                station_branch__station_id=self.request.station_id
            )
        if self.request.user.role == User.UserRoles.StationBranchManager:
            return self.queryset.filter(
                station_branch__station__branches__managers__user=self.request.user
            )
        return self.queryset
