from django_filters import DateFilter
from django_filters.rest_framework import FilterSet

from apps.accounting.models import StationKhaznaTransaction


class StationKhaznaTransactionFilter(FilterSet):
    created_from = DateFilter(field_name="created_at", lookup_expr="gte")
    created_to = DateFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = StationKhaznaTransaction
        fields = [
            "station",
            "created_from",
            "created_to",
            "is_incoming",
            "status",
            "method",
            "is_unpaid",
            "is_internal",
        ]
