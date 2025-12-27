from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.accounting.api.v1.serializers.company_transaction_serializer import (
    ListCompanyKhaznaTransactionSerializer,
)
from apps.accounting.models import CompanyKhaznaTransaction
from apps.companies.api.v1.serializers.car_operation_serializer import (
    ListCompanyHomeCarOperationSerializer,
)
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Car, Company, CompanyBranch
from apps.companies.models.operation_model import CarOperation


def company_home_for_owner(company_id):
    branches_id = CompanyBranch.objects.filter(company_id=company_id).values_list(
        "id", flat=True
    )

    branches_filter = Q(branches__id__in=set(branches_id))

    diesel_car_filter = Q(
        branches__cars__fuel_type=Car.FuelType.DIESEL, branches__id__in=branches_id
    )
    gasoline_car_filter = Q(
        branches__cars__fuel_type=Car.FuelType.GASOLINE,
        branches__id__in=branches_id,
    )
    drivers_lincense_expiration_date_filter = Q(
        branches__drivers__lincense_expiration_date__lt=timezone.localtime().date(),
        branches__id__in=branches_id,
    )
    drivers_lincense_expiration_date_filter_30_days = Q(
        branches__drivers__lincense_expiration_date__lt=timezone.localtime().date()
        - timedelta(days=30),
        branches__id__in=branches_id,
    )

    company = (
        Company.objects.filter(id=company_id)
        .annotate(
            total_cars_count=Count(
                "branches__cars", distinct=True, filter=branches_filter
            ),
            diesel_cars_count=Count(
                "branches__cars", filter=diesel_car_filter, distinct=True
            ),
            gasoline_cars_count=Count(
                "branches__cars", filter=gasoline_car_filter, distinct=True
            ),
            total_drivers_count=Count(
                "branches__drivers", distinct=True, filter=branches_filter
            ),
            total_drivers_with_lincense_expiration_date=Count(
                "branches__drivers",
                filter=drivers_lincense_expiration_date_filter,
                distinct=True,
            ),
            total_drivers_with_lincense_expiration_date_30_days=Count(
                "branches__drivers",
                filter=drivers_lincense_expiration_date_filter_30_days,
                distinct=True,
            ),
            total_branches_count=Count(
                "branches", distinct=True, filter=branches_filter
            ),
            cars_balance=Sum(
                "branches__cars__balance", filter=branches_filter, distinct=True
            ),
            branches_balance=Sum(
                "branches__balance", filter=branches_filter, distinct=True
            ),
        )
        .first()
    )
    if not company:
        return Response(
            {"message": "Company not found"}, status=status.HTTP_404_NOT_FOUND
        )
    cash_requests_balance = (
        CompanyCashRequest.objects.filter(
            driver__branch__in=branches_id,
            status=CompanyCashRequest.Status.IN_PROGRESS,
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )
    company.cars_balance = company.cars_balance if company.cars_balance else 0
    company.branches_balance = (
        company.branches_balance if company.branches_balance else 0
    )

    base_balance = company.balance if company.balance else 0
    total_balance = (
        company.balance
        + company.cars_balance
        + company.branches_balance
        + cash_requests_balance
    )

    response_data = {
        "name": company.name,
        "total_cars_count": company.total_cars_count,
        "diesel_cars_count": company.diesel_cars_count,
        "gasoline_cars_count": company.gasoline_cars_count,
        "total_drivers_count": company.total_drivers_count,
        "total_drivers_with_lincense_expiration_date": company.total_drivers_with_lincense_expiration_date,
        "total_drivers_with_lincense_expiration_date_30_days": company.total_drivers_with_lincense_expiration_date_30_days,
        "total_branches_count": company.total_branches_count,
        "total_branch_count": company.total_branches_count,
        "balance": base_balance,
        "cars_balance": company.cars_balance if company.cars_balance else 0,
        "branches_balance": (
            company.branches_balance if company.branches_balance else 0
        ),
        "cash_requests_balance": cash_requests_balance,
        "total_balance": total_balance if total_balance else 0,
    }

    response_data["car_operations"] = ListCompanyHomeCarOperationSerializer(
        CarOperation.objects.filter(car__branch__in=branches_id).order_by("-id")[:3],
        many=True,
    ).data
    company_transactions = (
        CompanyKhaznaTransaction.objects.filter(company__branches__in=branches_id)
        .distinct()
        .order_by("-id")[:3]
    )
    response_data["company_transactions"] = ListCompanyKhaznaTransactionSerializer(
        company_transactions,
        many=True,
    ).data

    response_data["branches"] = branches_id
    return response_data
