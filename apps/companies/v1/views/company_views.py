import uuid
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Count, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView, Response, status

from apps.accounting.models import CompanyKhaznaTransaction
from apps.companies.models.company_models import Car, Company, CompanyBranch
from apps.companies.v1.filters import CompanyBranchFilter
from apps.companies.v1.serializers.branch_serializers import (
    BranchBalanceUpdateSerializer,
    CompanyBranchAssignManagersSerializer,
    CompanyBranchSerializer,
    ListCompanyBranchSerializer,
    RetrieveCompanyBranchSerializer,
)
from apps.companies.v1.serializers.company_serializer import (
    CompanyHomeSerializer,
    CompanySerializer,
    ListCompanySerializer,
)
from apps.shared.base_exception_class import CustomValidationError
from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.users.models import CompanyBranchManager, User


class CompanyViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = Company.objects.select_related("district").order_by("-id")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListCompanySerializer
        return CompanySerializer


class CompanyBranchViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = (
        CompanyBranch.objects.select_related("district__city", "company")
        .prefetch_related("managers")
        .annotate(
            cars_count=Count("cars", distinct=True),
            drivers_count=Count("drivers", distinct=True),
            managers_count=Count("managers", distinct=True),
        )
        .order_by("-id")
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = CompanyBranchFilter

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            self.queryset = self.queryset.filter(company=self.request.company_id)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            self.queryset = self.queryset.filter(managers__user=self.request.user)
        return self.queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return ListCompanyBranchSerializer
        if self.action == "retrieve":
            return RetrieveCompanyBranchSerializer
        if self.action == "assign_managers":
            return CompanyBranchAssignManagersSerializer
        if self.action == "update_balance":
            return BranchBalanceUpdateSerializer
        return CompanyBranchSerializer

    @action(detail=True, methods=["post"], url_name="assign-managers")
    def assign_managers(self, request, *args, **kwargs):
        """
        Assign multiple managers to a branch
        Expects: {'managers': [list_of_user_ids]}
        """
        branch = self.get_object()

        serializer = CompanyBranchAssignManagersSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        # Atomic transaction for data consistency
        with transaction.atomic():
            # Clear existing managers
            branch.managers.all().delete()

            # Create new assignments
            CompanyBranchManager.objects.bulk_create(
                [
                    CompanyBranchManager(
                        user_id=user_id,
                        company_branch=branch,
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    for user_id in serializer.validated_data["managers"]
                ]
            )

        return Response(
            {"message": "تم تعيين المديرين بنجاح"}, status=status.HTTP_200_OK
        )

    @extend_schema(
        request=BranchBalanceUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "balance": {"type": "number", "format": "decimal"},
                    },
                    "required": ["balance"],
                },
                description="Current branch balance after the update.",
            )
        },
        examples=[
            OpenApiExample(
                "Add Balance Example",
                value={"amount": "100.00", "type": "add"},
                request_only=True,
            ),
            OpenApiExample(
                "Pull Balance Example",
                value={"amount": "50.00", "type": "subtract"},
                request_only=True,
            ),
        ],
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="update-balance",
        url_name="update_balance",
    )
    def update_balance(self, request, *args, **kwargs):
        company_branch = self.get_object()
        company = company_branch.company
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            if serializer.validated_data["type"] == "add":
                company.refresh_from_db()
                if company.balance >= serializer.validated_data["amount"]:
                    company.balance -= serializer.validated_data["amount"]
                    company.save()
                    company_branch.refresh_from_db()
                    company_branch.balance += serializer.validated_data["amount"]
                    company_branch.save()

                    CompanyKhaznaTransaction.objects.create(
                        amount=serializer.validated_data["amount"],
                        is_incoming=True,
                        status=CompanyKhaznaTransaction.TransactionStatus.APPROVED,
                        reference_code="int" + str(uuid.uuid4())[:8].upper(),
                        description="تم اضافة شحن رصيد فرع " + str(company_branch.name),
                        method=CompanyKhaznaTransaction.TransactionMethod.BANK,
                        company=company,
                        is_internal=True,
                    )
                else:
                    raise CustomValidationError(
                        message="الشركة لا تمتلك كافٍ من المال",
                        code="not_enough_balance",
                        errors=[],
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            elif serializer.validated_data["type"] == "subtract":
                company_branch.refresh_from_db()
                if company_branch.balance >= serializer.validated_data["amount"]:
                    company_branch.balance -= serializer.validated_data["amount"]
                    company_branch.save()
                    company.refresh_from_db()
                    company.balance += serializer.validated_data["amount"]
                    company.save()
                else:
                    raise CustomValidationError(
                        message="الفرع لا تمتلك كافٍ من المال",
                        code="not_enough_balance",
                        errors=[],
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

        return Response({"balance": company_branch.balance}, status=status.HTTP_200_OK)


class CompanyHomeView(APIView):

    def get(self, request, *args, **kwargs):
        diesel_car_filter = Q(branches__cars__fuel_type=Car.FuelType.DIESEL)
        gasoline_car_filter = Q(branches__cars__fuel_type=Car.FuelType.GASOLINE)
        drivers_lincense_expiration_date_filter = Q(
            branches__drivers__lincense_expiration_date__lt=datetime.now()
        )
        drivers_lincense_expiration_date_filter_30_days = Q(
            branches__drivers__lincense_expiration_date__lt=datetime.now()
            - timedelta(days=30)
        )
        company = (
            Company.objects.filter(id=request.company_id)
            .annotate(
                total_branch_count=Count("branches"),
                total_cars_count=Count("branches__cars"),
                diesel_cars_count=Count("branches__cars", filter=diesel_car_filter),
                gasoline_cars_count=Count("branches__cars", filter=gasoline_car_filter),
                total_drivers_count=Count("branches__drivers", distinct=True),
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
                total_branches_count=Count("branches"),
                cars_balance=Sum("branches__cars__balance"),
                branches_balance=Sum("branches__balance"),
                total_balance=Sum("balance")
                + Sum("branches__balance")
                + Sum("branches__cars__balance"),
            )
            .first()
        )
        serializer = CompanyHomeSerializer(company)
        return Response(serializer.data)
