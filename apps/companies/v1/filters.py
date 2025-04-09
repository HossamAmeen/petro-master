from django_filters import rest_framework as django_filters

from apps.companies.models.company_models import CompanyBranch
from apps.geo.models import City


class CompanyBranchFilter(django_filters.FilterSet):
    city = django_filters.ModelChoiceFilter(
        queryset=City.objects.all(), field_name="district__city"
    )

    class Meta:
        model = CompanyBranch
        fields = ["company", "city"]
