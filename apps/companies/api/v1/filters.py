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
        ]


class CarFilter(django_filters.FilterSet):
    fuel_type = django_filters.MultipleChoiceFilter(
        choices=Car.FuelType.choices, field_name="fuel_type"
    )

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
