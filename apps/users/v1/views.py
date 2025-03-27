from rest_framework import viewsets

from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.users.models import User

from .serializers import ListUserSerializer, UserSerializer, ListCompanyBranchManagerSerializer, CompanyBranchManagerSerializer


class UserViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related('created_by', 'updated_by').order_by('-id')

    def get_serializer_class(self):
        if self.action == 'list':
            return ListUserSerializer
        return UserSerializer


class CompanyBranchManagerViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = User.objects.filter(role=User.UserRoles.CompanyBranchManager).select_related('created_by', 'updated_by').order_by('-id')

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company_branch_managers__company_branch__company__owners=self.request.user)
        return self.queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ListCompanyBranchManagerSerializer
        return CompanyBranchManagerSerializer
