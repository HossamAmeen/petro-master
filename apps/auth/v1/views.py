from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.shared.base_exception_class import CustomValidationError
from apps.users.models import User
from apps.utilities.serializers import MessageErrorsSerializer

from .serializers import (
    LoginSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    SetNewPasswordSerializer,
)


class CompanyLoginAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                description="login successfully",
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        "Success Response",
                        value={
                            "message": "login successfully",
                            "refresh": "<refresh_token>",
                            "access": "<access_token>",
                            "user_name": "<user_name>",
                            "role": "<role>",
                        },
                    )
                ],
            ),
            400: MessageErrorsSerializer,
        },
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
            raise CustomValidationError(
                message="Invalid credentials",
                code="invalid_credentials",
                errors=[],
                status_code=status.HTTP_401_UNAUTHORIZED,
            )


class StationLoginAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                description="login successfully",
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        "Success Response",
                        value={
                            "message": "login successfully",
                            "refresh": "<refresh_token>",
                            "access": "<access_token>",
                            "user_name": "<user_name>",
                            "role": "<role>",
                        },
                    )
                ],
            ),
            400: MessageErrorsSerializer,
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            Q(phone_number=serializer.validated_data["identifier"])
            | Q(email=serializer.validated_data["identifier"]),
            is_active=True,
        ).first()
        station_roles = [User.UserRoles.StationManager, User.UserRoles.StationEmployee]
        if (
            user
            and user.check_password(serializer.validated_data["password"])
            and user.role in station_roles
        ):
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            access_token["user_name"] = user.name
            access_token["role"] = user.role
            access_token["station_id"] = user.stationuser.station.id
            data = {
                "refresh": str(refresh),
                "access": str(access_token),
                "user_name": user.name,
                "role": user.role,
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            raise CustomValidationError(
                message="Invalid credentials",
                code="invalid_credentials",
                errors=[],
                status_code=status.HTTP_401_UNAUTHORIZED,
            )


class ProfileAPIView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


class PasswordResetRequestAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset request sent successfully"
            ),
            404: OpenApiResponse(description="User not found"),
            500: OpenApiResponse(description="Failed to send password reset request"),
        },
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            email=serializer.validated_data["email"], is_active=True
        ).first()

        if user:
            reset_token = user.create_password_reset_token()
            reset_url = reverse("password_reset_confirm", kwargs={"token": reset_token})
            reset_link = request.build_absolute_uri(reset_url)

            subject = "Password Reset Request"
            # message = (
            #     f"Please click the following link to reset your password: {reset_link}"
            # )
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            html_message = f"""<html><body><p>Please click the following link to reset your password:</p> <p><a href='{reset_link}'>Reset Password</a></p> <p>If the link doesn't work, copy and paste this URL into your browser:</p> <p>{reset_link}</p></body></html>"""  # noqa
            try:
                send_mail(
                    subject,
                    from_email,
                    recipient_list,
                    fail_silently=False,
                    html_message=html_message,
                )
                return Response(
                    {"message": "Password reset request sent successfully"},
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                raise CustomValidationError(
                    message="Failed to send password reset request",
                    code="failed_to_send_password_reset_request",
                    errors=[str(e)],
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        else:
            raise CustomValidationError(
                message="User not found",
                code="user_not_found",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )


class PasswordResetConfirmAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = SetNewPasswordSerializer

    def get(self, request, token):
        user = User.objects.filter(reset_password_token=token).first()
        if not user:
            return render(
                request,
                "reset_password_form.html",
                {
                    "token_valid": False,
                    "message": "Invalid or expired token.",
                    "token": None,
                },
            )

        return render(
            request,
            "reset_password_form.html",
            {"token_valid": True, "token": token},
        )

    @extend_schema(
        request=SetNewPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successful"),
            400: OpenApiResponse(description="Invalid or expired reset link"),
            404: OpenApiResponse(description="User not found"),
            500: OpenApiResponse(description="Failed to reset password"),
        },
    )
    def post(self, request, token):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(reset_password_token=token)
            if user.is_valid_password_reset_token(token):
                new_password = serializer.validated_data["password"]
                user.set_password(new_password)
                user.reset_password_token = None
                user.reset_password_token_created_at = None
                user.save()
                return Response(
                    {"detail": "Password reset successful."}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"detail": "Invalid or expired reset link."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST
            )
