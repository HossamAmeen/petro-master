from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

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
from apps.users.models import User

from .serializers import (
    CompanyBranchSerializer,
    CompanySerializer,
    DriverSerializer,
    ListCompanyBranchSerializer,
    ListCompanySerializer,
    ListDriverSerializer,
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
        if self.request.method == "GET":
            return ListCompanyBranchSerializer
        return CompanyBranchSerializer


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
