from django_filters import rest_framework as django_filters

from apps.companies.models.company_models import CompanyBranch
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
    start_date = django_filters.DateFilter(field_name="start_time", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="end_time", lookup_expr="lte")

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
