from django_filters import rest_framework as django_filters

from apps.users.models import CompanyUser


class CompanyBranchManagerFilter(django_filters.FilterSet):
    branch = django_filters.NumberFilter(
        field_name="company_branch_managers__company_branch"
    )

    class Meta:
        model = CompanyUser
        fields = ["branch"]
