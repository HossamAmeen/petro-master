from rest_framework import viewsets

from apps.shared.mixins.inject_user_mixins import InjectUserMixin

from .models import Company, CompanyBranch, Driver
from .serializers import (CompanyBranchSerializer, CompanySerializer,
                          DriverSerializer, ListCompanyBranchSerializer,
                          ListCompanySerializer, ListDriverSerializer)


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.select_related('district').order_by('-id')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ListCompanySerializer
        return CompanySerializer


class DriverViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = Driver.objects.select_related(
        'branch__district').order_by('-id')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ListDriverSerializer
        return DriverSerializer


class CompanyBranchViewSet(viewsets.ModelViewSet):
    queryset = CompanyBranch.objects.select_related(
        'district', 'company').order_by('-id')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ListCompanyBranchSerializer
        return CompanyBranchSerializer
