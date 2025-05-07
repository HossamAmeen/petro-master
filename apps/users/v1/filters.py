from django_filters import rest_framework as django_filters

from apps.users.models import CompanyUser


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
