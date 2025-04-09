from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User

from .serializers import LoginSerializer, ProfileSerializer


class CompanyLoginAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={200: openapi.Response("JWT tokens")},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            Q(phone_number=serializer.validated_data["identifier"])
            | Q(email=serializer.validated_data["identifier"]),
            is_active=True,
        ).first()
        company_roles = [
            User.UserRoles.CompanyOwner,
            User.UserRoles.CompanyBranchManager,
        ]
        if (
            user
            and user.check_password(serializer.validated_data["password"])
            and user.role in company_roles
        ):
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            access_token["user_name"] = user.name
            access_token["role"] = user.role
            access_token["company_id"] = user.companyuser.company.id
            data = {
                "refresh": str(refresh),
                "access": str(access_token),
                "user_name": user.name,
                "role": user.role,
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )


class ProfileAPIView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user
