from django_filters import rest_framework as django_filters

from apps.companies.models.company_models import Car, Company, CompanyBranch, Driver
from apps.companies.models.operation_model import CarOperation
from apps.geo.models import City


class CompanyBranchFilter(django_filters.FilterSet):
    city = django_filters.ModelChoiceFilter(
        queryset=City.objects.all(), field_name="district__city"
    )

    class Meta:
        model = CompanyBranch
        fields = ["company", "city"]


class CarOperationFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name="start_time__date", lookup_expr="gte"
    )
    end_date = django_filters.DateFilter(field_name="end_time__date", lookup_expr="lte")
    status = django_filters.CharFilter(
        method="filter_by_status",
        help_text="Filter by status example statusing=pending,in_progress,completed,cancelled",
    )

    def filter_by_status(self, queryset, name, value):
        status_values = value.split(",")
        return queryset.filter(status__in=status_values)

    class Meta:
        model = CarOperation
        fields = [
            "car",
            "driver",
            "station_branch",
            "worker",
            "service",
            "start_date",
            "end_date",
            "status",
        ]


class CarFilter(django_filters.FilterSet):
    fuel_type = django_filters.CharFilter(
        method="filter_by_fuel_type",
        help_text="Filter by fuel type example fuel_type=diesel,solar,electric",
    )

    def filter_by_fuel_type(self, queryset, name, value):
        fuel_type_values = value.split(",")
        return queryset.filter(fuel_type__in=fuel_type_values)

    class Meta:
        model = Car
        fields = [
            "branch",
            "fuel_type",
            "city",
            "is_with_odometer",
        ]


class DriverFilter(django_filters.FilterSet):
    city = django_filters.NumberFilter(field_name="branch__district__city")

    class Meta:
        model = Driver
        fields = ["branch", "city"]


class CompanyFilter(django_filters.FilterSet):
    city = django_filters.ModelChoiceFilter(
        queryset=City.objects.all(), field_name="district__city"
    )

    class Meta:
        model = Company
        fields = ["district", "city"]
