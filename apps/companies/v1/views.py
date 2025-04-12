from django.db import transaction
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import Response, status

from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Company, CompanyBranch, Driver
from apps.companies.v1.filters import CompanyBranchFilter
from apps.companies.v1.serializers import (
    CompanyCashRequestSerializer,
    ListCompanyCashRequestSerializer,
)
from apps.shared.mixins.inject_user_mixins import (
    InjectCompanyUserMixin,
    InjectUserMixin,
)
from apps.users.models import CompanyBranchManager, User

from .serializers import (
    CompanyBranchAssignManagersSerializer,
    CompanyBranchSerializer,
    CompanySerializer,
    DriverSerializer,
    ListCompanyBranchSerializer,
    ListCompanySerializer,
    ListDriverSerializer,
    RetrieveCompanyBranchSerializer,
)


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
            cars_count=Count("cars"),
            drivers_count=Count("drivers"),
            managers_count=Count("managers", distinct=True),
        )
        .order_by("-id")
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = CompanyBranchFilter

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company__owners=self.request.user)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(managers__user=self.request.user)
        return self.queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ListCompanyBranchSerializer
        if self.action == "retrieve":
            return RetrieveCompanyBranchSerializer
        if self.action == "assign_managers":
            return CompanyBranchAssignManagersSerializer
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


class DriverViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = Driver.objects.select_related("branch__district").order_by("-id")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListDriverSerializer
        return DriverSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(branch__company__owners=self.request.user)
        return self.queryset


class CompanyCashRequestViewSet(InjectCompanyUserMixin, viewsets.ModelViewSet):
    queryset = CompanyCashRequest.objects.select_related("driver", "station").order_by(
        "-id"
    )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    http_method_names = ["get", "post", "patch"]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListCompanyCashRequestSerializer
        return CompanyCashRequestSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company__owners=self.request.user)
        return self.queryset
