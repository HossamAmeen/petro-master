from rest_framework import viewsets

from apps.companies.models.operation_model import CarOperation
from apps.companies.v1.filters import CarOperationFilter
from apps.companies.v1.serializers.car_operation_serializer import (
    ListCarOperationSerializer,
)


class CarOperationViewSet(viewsets.ModelViewSet):
    queryset = CarOperation.objects.select_related(
        "car", "driver", "station_branch", "worker", "service"
    ).order_by("-id")
    serializer_class = ListCarOperationSerializer
    filterset_class = CarOperationFilter
    search_fields = [
        "code",
        "car__code",
        "driver__name",
        "station_branch__name",
        "worker__name",
    ]

    def export(self, request, *args, **kwargs):
        pass
