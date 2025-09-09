from django_filters import rest_framework as django_filters

from apps.users.models import CompanyUser, StationOwner


class CompanyBranchManagerFilter(django_filters.FilterSet):
    branch = django_filters.NumberFilter(
        field_name="company_branch_managers__company_branch"
    )
    city = django_filters.NumberFilter(
        field_name="company_branch_managers__company_branch__district__city"
    )

    class Meta:
        model = CompanyUser
        fields = ["branch", "city"]


class StationBranchManagerFilter(django_filters.FilterSet):
    station = django_filters.NumberFilter(
        field_name="station_branch_managers__station_branch"
    )
    city = django_filters.NumberFilter(
        field_name="station_branch_managers__station_branch__district__city"
    )
    branch = django_filters.NumberFilter(
        field_name="station_branch_managers__station_branch_managers__station_branch"
    )

    class Meta:
        model = StationOwner
        fields = ["station", "city", "branch"]
