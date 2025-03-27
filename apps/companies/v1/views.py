from django.db.models import Count
from rest_framework import viewsets

from apps.companies.models.company_models import Company, CompanyBranch, Driver
from apps.shared.mixins.inject_user_mixins import InjectUserMixin
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
    queryset = Company.objects.select_related('district').order_by('-id')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ListCompanySerializer
        return CompanySerializer


class CompanyBranchViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = CompanyBranch.objects.select_related(
        'district__city', 'company').annotate(
            cars_count=Count("cars"),
            drivers_count=Count("drivers"),
            managers_count=Count("managers", distinct=True)
        ).order_by('-id')

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company__owners=self.request.user)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(managers__user=self.request.user)
        return self.queryset

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ListCompanyBranchSerializer
        return CompanyBranchSerializer


class DriverViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = Driver.objects.select_related(
        'branch__district').order_by('-id')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ListDriverSerializer
        return DriverSerializer

    def get_queryset(self):
        print(self.request.user.companyuser.company.id)
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(branch__company__owners=self.request.user)
        return self.queryset
