from django.forms.widgets import DateInput
from django_filters import DateFilter
from django_filters.rest_framework import FilterSet

from apps.accounting.models import StationKhaznaTransaction


class StationKhaznaTransactionFilter(FilterSet):
    created_from = DateFilter(
        field_name="created_at__date",
        lookup_expr="gte",
        format="%Y-%m-%d",
        label="Created From",
        widget=DateInput(attrs={"type": "date"}),
        help_text="Filter transactions created on or after this date. Format: YYYY-MM-DD",
    )
    created_to = DateFilter(
        field_name="created_at__date",
        lookup_expr="lte",
        format="%Y-%m-%d",
        label="Created To",
        widget=DateInput(attrs={"type": "date"}),
        help_text="Filter transactions created on or before this date. Format: YYYY-MM-DD",
    )
    approved_from = DateFilter(
        field_name="approved_at__date",
        lookup_expr="gte",
        format="%Y-%m-%d",
        label="Approved From",
        widget=DateInput(attrs={"type": "date"}),
        help_text="Filter transactions approved on or after this date. Format: YYYY-MM-DD",
    )
    approved_to = DateFilter(
        field_name="approved_at__date",
        lookup_expr="lte",
        format="%Y-%m-%d",
        label="Approved To",
        widget=DateInput(attrs={"type": "date"}),
        help_text="Filter transactions approved on or before this date. Format: YYYY-MM-DD",
    )

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
            "approved_from",
            "approved_to",
        ]
