from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.views import Response

from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.users.models import CompanyUser, FirebaseToken, User

from .serializers.company_user_serializer import (
    CompanyBranchManagerSerializer,
    ListCompanyBranchManagerSerializer,
)
from .serializers.user_serializers import (
    FirebaseTokenSerializer,
    ListUserSerializer,
    UserSerializer,
)


class UserViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related("created_by", "updated_by").order_by("-id")

    def get_serializer_class(self):
        if self.action == "list":
            return ListUserSerializer
        return UserSerializer


class CompanyBranchManagerViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = (
        CompanyUser.objects.filter(role=User.UserRoles.CompanyBranchManager)
        .select_related("created_by", "updated_by")
        .order_by("-id")
    )

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(company=self.request.company_id)
        return self.queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ListCompanyBranchManagerSerializer
        return CompanyBranchManagerSerializer


class FirebaseTokenViewSet(viewsets.ModelViewSet):
    http_method_names = ["post", "delete"]

    def get_queryset(self):
        return FirebaseToken.objects.filter(user=self.request.user).order_by("-id")

    def get_serializer_class(self):
        return FirebaseTokenSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["delete"], url_path="delete-by-token")
    def delete_by_token(self, request, *args, **kwargs):
        token_string = request.data.get("token")
        if not token_string:
            return Response(
                {"error": "Token string is required in the request body."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            instance = FirebaseToken.objects.get(user=request.user, token=token_string)
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except FirebaseToken.DoesNotExist:
            return Response(
                {"error": "Firebase token not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )
