from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from apps.users.models import StationOwner, User
from apps.users.v1.filters import StationBranchManagerFilter
from apps.users.v1.serializers.station_serializer import (
    ListStationBranchManagerSerializer,
    ListStationOwnerSerializer,
    StationBranchManagerCreationSerializer,
    StationBranchManagerUpdateSerializer,
    StationOwnerSerializer,
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
        if self.request.method == "POST":
            return StationBranchManagerCreationSerializer
        if self.request.method == "PATCH":
            return StationBranchManagerUpdateSerializer
