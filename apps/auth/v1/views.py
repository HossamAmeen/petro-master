from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User

from .serializers import LoginSerializer


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

        user = User.objects.filter(Q(phone_number=serializer.validated_data['identifier'])
                                   | Q(email=serializer.validated_data['identifier']), is_active=True).first()
        company_roles = [User.UserRoles.CompanyOwner, User.UserRoles.CompanyBranchManager]
        if user and user.check_password(serializer.validated_data['password']) and user.role in company_roles:
            refresh = RefreshToken.for_user(user)
            data = {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
