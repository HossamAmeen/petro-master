from django_filters import rest_framework as filters

from apps.companies.models.company_cash_models import CompanyCashRequest


class CashRequestFilter(filters.FilterSet):
    approved_from = filters.DateFilter(field_name="modified__date__gte")
    approved_to = filters.DateFilter(field_name="modified__date__lte")
    station_branch = filters.NumberFilter(field_name="approved_by__branch_id")
    company_branch = filters.NumberFilter(field_name="driver__branch_id")

    class Meta:
        model = CompanyCashRequest
        fields = [
            "status",
            "approved_by",
            "driver",
            "station",
            "company",
            "approved_from",
            "approved_to",
            "station_branch",
            "company_branch",
        ]
