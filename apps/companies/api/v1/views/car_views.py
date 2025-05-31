from django.db import transaction
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView, Response, status

from apps.accounting.helpers import generate_company_transaction
from apps.accounting.models import CompanyKhaznaTransaction, KhaznaTransaction
from apps.companies.api.v1.filters import CarFilter, DriverFilter
from apps.companies.api.v1.serializers.car_serializer import (
    CarBalanceUpdateSerializer,
    CarSerializer,
    ListCarSerializer,
)
from apps.companies.api.v1.serializers.driver_serializer import (
    DriverSerializer,
    ListDriverSerializer,
)
from apps.companies.models.company_models import Car, Driver
from apps.notifications.models import Notification
from apps.shared.base_exception_class import CustomValidationError
from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.users.models import User


class DriverViewSet(InjectUserMixin, viewsets.ModelViewSet):
    filterset_class = DriverFilter
    queryset = Driver.objects.select_related("branch__district").order_by("-id")
    search_fields = [
        "name",
        "branch__name",
        "branch__district__name",
    ]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListDriverSerializer
        return DriverSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(branch__company=self.request.company_id)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(branch__managers__user=self.request.user)
        return self.queryset


class CarViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = Car.objects.select_related("branch__district").order_by("-id")
    filterset_class = CarFilter
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
            return self.queryset.filter(branch__company=self.request.company_id)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(branch__managers__user=self.request.user)
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

        if self.request.user.role == User.UserRoles.CompanyOwner:
            parent_object = car.branch.company
            notification_users = list(
                car.branch.managers.values_list("user_id", flat=True)
            )
            notification_users.append(request.user.id)
        elif self.request.user.role == User.UserRoles.CompanyBranchManager:
            parent_object = car.branch
            notification_users = list(
                car.branch.managers.exclude(user=request.user).values_list(
                    "user_id", flat=True
                )
            )
            notification_users.extend(
                car.branch.company.owners.values_list("user_id", flat=True)
            )

        with transaction.atomic():
            if serializer.validated_data["type"] == "add":
                car.refresh_from_db()
                if parent_object.balance >= serializer.validated_data["amount"]:
                    car.balance += serializer.validated_data["amount"]
                    car.save()

                    parent_object.refresh_from_db()
                    parent_object.balance -= serializer.validated_data["amount"]
                    parent_object.save()
                    message = f"تم شحن رصيد السيارة ({car.plate}) برصيد {serializer.validated_data['amount']} التابعة لفرع {car.branch.name}"
                    generate_company_transaction(
                        company_id=self.request.company_id,
                        amount=serializer.validated_data["amount"],
                        status=KhaznaTransaction.TransactionStatus.APPROVED,
                        description=message,
                        is_internal=True,
                        for_what=CompanyKhaznaTransaction.ForWhat.CAR,
                        created_by_id=request.user.id,
                    )
                    for user_id in notification_users:
                        Notification.objects.create(
                            user_id=user_id,
                            title=message,
                            description=message,
                            type=Notification.NotificationType.MONEY,
                        )

                else:
                    raise CustomValidationError(
                        message="السيارة لا تمتلك كافٍ من المال",
                        code="not_enough_balance",
                        errors=[],
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            elif serializer.validated_data["type"] == "subtract":
                car.refresh_from_db()
                if parent_object.balance >= serializer.validated_data["amount"]:
                    car.balance -= serializer.validated_data["amount"]
                    car.save()

                    parent_object.refresh_from_db()
                    parent_object.balance += serializer.validated_data["amount"]
                    parent_object.save()
                    message = f"تم سحب رصيد السيارة ({car.plate}) برصيد {serializer.validated_data['amount']} التابعة لفرع {car.branch.name}"
                    generate_company_transaction(
                        company_id=self.request.company_id,
                        amount=serializer.validated_data["amount"],
                        status=KhaznaTransaction.TransactionStatus.APPROVED,
                        description=message,
                        is_internal=True,
                        for_what=CompanyKhaznaTransaction.ForWhat.CAR,
                        created_by_id=request.user.id,
                    )
                    for user_id in notification_users:
                        Notification.objects.create(
                            user_id=user_id,
                            title=message,
                            description=message,
                            type=Notification.NotificationType.MONEY,
                        )
                else:
                    raise CustomValidationError(
                        message="السيارة لا تمتلك كافٍ من المال",
                        code="not_enough_balance",
                        errors=[],
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

        return Response({"balance": car.balance}, status=status.HTTP_200_OK)


class CarDetailsView(APIView):
    def get(self, request, car_code):
        car = Car.objects.filter(code=car_code.strip()).first()
        if not car:
            raise CustomValidationError(
                message="كود السيارة هذا لا يعمل او غير مفعل الان.",
                code="car_code_not_found",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if not car.is_available_today():
            raise CustomValidationError(
                message="السيارة غير مفعلة",
                code="car_not_active",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return Response(CarSerializer(car).data)


class VerifyDriverView(APIView):
    def post(self, request, driver_code, car_code):
        driver = Driver.objects.filter(code=driver_code.strip()).first()
        if not driver:
            raise CustomValidationError(
                message="كود السائق هذا لا يعمل او غير مفعل الان.",
                code="driver_code_not_found",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )
        car = Car.objects.filter(code=car_code.strip()).first()
        if not car:
            raise CustomValidationError(
                message="كود السيارة هذا لا يعمل او غير مفعل الان.",
                code="car_code_not_found",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if driver.branch.company_id != car.branch.company_id:
            raise CustomValidationError(
                message="السائق لا ينتمي للشركة",
                code="driver_not_belongs_to_company",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"message": "تم التحقق من السائق بنجاح"}, status=status.HTTP_200_OK
        )
