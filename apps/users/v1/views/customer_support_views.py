from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.shared.permissions import AdminPermission
from apps.users.models import CustomerSupport
from apps.users.v1.serializers.user_serializers import (
    CreateCustomerSupportSerializer,
    ListCustomerSupportSerializer,
)


class CustomerSupportViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = CustomerSupport.objects.select_related(
        "created_by", "updated_by"
    ).order_by("-id")
    permission_classes = [IsAuthenticated, AdminPermission]
    filterset_fields = ["is_active"]
    search_fields = ["name", "phone_number", "email"]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return ListCustomerSupportSerializer
        return CreateCustomerSupportSerializer
