from django_filters import rest_framework as django_filters

from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import StationBranch


class StationBranchFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(field_name="district__city")

    class Meta:
        model = StationBranch
        fields = ["station", "city", "is_for_landing_page"]


class ServiceFilter(django_filters.FilterSet):
    station = django_filters.NumberFilter(
        field_name="station_branch_services__station_branch__station"
    )
    station_branch = django_filters.NumberFilter(
        field_name="station_branch_services__station_branch"
    )
    type = django_filters.MultipleChoiceFilter(
        choices=Service.ServiceType.choices, field_name="type"
    )

    class Meta:
        model = Service
        fields = ["type", "station"]
