from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from apps.users.models import StationBranchManager, StationOwner
from apps.users.v1.serializers.station_serializer import (
    ListStationBranchManagerSerializer,
    ListStationOwnerSerializer,
    StationBranchManagerSerializer,
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
    queryset = StationBranchManager.objects.select_related("station_branch", "user").order_by("-id")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["station_branch", "user"]
    search_fields = ["name", "phone_number", "email"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListStationBranchManagerSerializer
        return StationBranchManagerSerializer
