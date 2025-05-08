from django_filters import rest_framework as django_filters

from apps.stations.models.stations_models import StationBranch


class StationBranchFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(field_name="district__city")

    class Meta:
        model = StationBranch
        fields = ["station", "city"]
