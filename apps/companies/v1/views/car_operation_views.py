from rest_framework import viewsets

from apps.companies.models.operation_model import CarOperation
from apps.companies.v1.serializers.car_operation_serializer import (
    listCarOperationSerializer,
)


class CarOperationViewSet(viewsets.ModelViewSet):
    queryset = CarOperation.objects.select_related(
        "car", "driver", "station_branch", "worker", "service"
    ).order_by("-id")
    serializer_class = listCarOperationSerializer
    filterset_fields = [
        "car",
        "driver",
        "station_branch",
        "worker",
        "service",
        "created__gte",
        "created__lte",
    ]
    search_fields = [
        "code",
        "car__code",
        "driver__name",
        "station_branch__name",
        "worker__name",
    ]
