from django.db import transaction
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import Response, status

from apps.companies.models.company_models import Car, Driver
from apps.companies.v1.serializers.car_serializer import (
    CarBalanceUpdateSerializer,
    CarSerializer,
    ListCarSerializer,
)
from apps.companies.v1.serializers.driver_serializer import (
    DriverSerializer,
    ListDriverSerializer,
)
from apps.shared.base_exception_class import CustomValidationError
from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.users.models import User


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


class CarViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = Car.objects.select_related("branch__district").order_by("-id")
    filterset_fields = ["branch", "fuel_type", "city", "is_with_odometer"]
    search_fields = [
        "code",
        "plate_number",
        "plate_character",
        "lincense_number",
        "name",
        "branch__name",
        "branch__district__name",
    ]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListCarSerializer
        return CarSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(branch__company__owners=self.request.user)
        return self.queryset

    @extend_schema(
        request=CarBalanceUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "balance": {"type": "number", "format": "decimal"},
                    },
                    "required": ["balance"],
                },
                description="Current car balance after the update.",
            )
        },
        examples=[
            OpenApiExample(
                "Add Balance Example",
                value={"amount": "100.00", "type": "add"},
                request_only=True,
            ),
            OpenApiExample(
                "Pull Balance Example",
                value={"amount": "50.00", "type": "subtract"},
                request_only=True,
            ),
        ],
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="update-balance",
        url_name="update_balance",
    )
    def update_balance(self, request, *args, **kwargs):
        car = self.get_object()
        serializer = CarBalanceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            if serializer.validated_data["type"] == "add":
                car.refresh_from_db()
                if car.balance >= serializer.validated_data["amount"]:
                    car.balance += serializer.validated_data["amount"]
                    car.save()

                    branch = car.branch
                    branch.refresh_from_db()
                    branch.balance += serializer.validated_data["amount"]
                    branch.save()
                else:
                    raise CustomValidationError(
                        message="السيارة لا تمتلك كافٍ من المال",
                        code="not_enough_balance",
                        errors=[],
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            elif serializer.validated_data["type"] == "subtract":
                car.refresh_from_db()
                if car.balance >= serializer.validated_data["amount"]:
                    car.balance -= serializer.validated_data["amount"]
                    car.save()

                    branch = car.branch
                    branch.refresh_from_db()
                    branch.balance += serializer.validated_data["amount"]
                    branch.save()
                else:
                    raise CustomValidationError(
                        message="السيارة لا تمتلك كافٍ من المال",
                        code="not_enough_balance",
                        errors=[],
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

        return Response({"balance": car.balance}, status=status.HTTP_200_OK)
