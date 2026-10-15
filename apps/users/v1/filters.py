from django_filters import rest_framework as django_filters

from apps.users.models import CompanyUser, StationOwner, User, Worker


class UserFilter(django_filters.FilterSet):

    class Meta:
        model = User
        fields = ["role", "is_active"]


class CompanyBranchManagerFilter(django_filters.FilterSet):
    company = django_filters.NumberFilter(field_name="company")
    company_id = django_filters.NumberFilter(field_name="company")
    branch = django_filters.NumberFilter(
        field_name="company_branch_managers__company_branch"
    )
    city = django_filters.NumberFilter(
        field_name="company_branch_managers__company_branch__district__city"
    )

    class Meta:
        model = CompanyUser
        fields = ["company", "company_id", "branch", "city"]


class CompanyOwnerFilter(django_filters.FilterSet):
    company = django_filters.NumberFilter(field_name="company")
    company_id = django_filters.NumberFilter(field_name="company")

    class Meta:
        model = CompanyUser
        fields = ["company", "company_id"]


class WorkerFilter(django_filters.FilterSet):
    branch = django_filters.NumberFilter(field_name="station_branch")
    station = django_filters.NumberFilter(field_name="station_branch__station")

    class Meta:
        model = Worker
        fields = ["station_branch", "branch", "station"]


class StationOwnerFilter(django_filters.FilterSet):
    city = django_filters.NumberFilter(field_name="district__city")

    class Meta:
        model = StationOwner
        fields = ["station", "city", "role"]


class StationBranchManagerFilter(django_filters.FilterSet):
    station = django_filters.NumberFilter(
        field_name="station_branch_managers__station_branch"
    )
    city = django_filters.NumberFilter(
        field_name="station_branch_managers__station_branch__district__city"
    )
    branch = django_filters.NumberFilter(
        field_name="station_branch_managers__station_branch"
    )

    class Meta:
        model = StationOwner
        fields = ["station", "city", "branch", "role"]
