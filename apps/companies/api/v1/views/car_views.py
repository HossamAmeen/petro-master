import math

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
from apps.companies.models.operation_model import CarOperation
from apps.notifications.models import Notification
from apps.shared.base_exception_class import CustomValidationError
from apps.shared.constants import COLOR_CHOICES_HEX
from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.shared.permissions import StationWorkerPermission
from apps.users.models import User


class DriverViewSet(InjectUserMixin, viewsets.ModelViewSet):
    filterset_class = DriverFilter
    queryset = Driver.objects.select_related(
        "branch__district", "branch__company"
    ).order_by("-id")
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
    queryset = Car.objects.select_related(
        "branch__district", "branch__company"
    ).order_by("-id")
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
        if car.is_blocked_balance_update:
            raise CustomValidationError(
                {
                    "error": "لا يمكن تحديث رصيد السيارة حاليا لانها في منتصف عملية، يرجى اتمام العملية اولا"
                },
                code="not_found",
            )
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
                car.branch.company.owners.values_list("id", flat=True)
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
                        message="الرصيد غير كافٍ",
                        code="not_enough_balance",
                        errors=[],
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            elif serializer.validated_data["type"] == "subtract":
                car.refresh_from_db()
                if car.balance >= serializer.validated_data["amount"]:
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


class VerifyDriverView(APIView):
    permission_classes = [IsAuthenticated, StationWorkerPermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "driver_code",
                type=str,
                required=True,
                description="The unique code of the driver to verify.",
            ),
            OpenApiParameter(
                "car_code",
                type=str,
                required=True,
                description="The unique code of the car to verify.",
            ),
            OpenApiParameter(
                "service_type",
                type=str,
                required=True,
                description="Type of service requested (e.g., petrol,other).",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "car": {
                            "type": "object",
                            "properties": {
                                "plate_number": {"type": "string"},
                                "plate_character": {"type": "string"},
                                "plate_color": {"type": "string"},
                                "fuel_type": {"type": "string"},
                                "liter_count": {"type": "integer"},
                                "cost": {"type": "number"},
                                "code": {"type": "string"},
                            },
                        },
                        "operation_id": {"type": "integer"},
                    },
                    "required": ["message", "car", "operation_id"],
                }
            )
        },
    )
    @transaction.atomic
    def post(self, request, driver_code, car_code, service_type):
        car = (
            Car.objects.filter(code=car_code.strip())
            .select_related("branch__company")
            .first()
        )
        if not car:
            raise CustomValidationError(
                message="كود السيارة هذا لا يعمل او غير مفعل الان.",
                code="car_code_not_found",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )

        company_branch = car.branch
        if not company_branch.company.is_active:
            raise CustomValidationError(
                message="حساب الشركه معلق مؤقتا",
                code="company_not_active",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )

        driver = Driver.objects.filter(code=driver_code.strip()).first()
        if not driver:
            raise CustomValidationError(
                message="كود السائق هذا لا يعمل او غير مفعل الان.",
                code="driver_code_not_found",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if driver.branch.company_id != company_branch.company_id:
            raise CustomValidationError(
                message="السائق لا ينتمي للشركة",
                code="driver_not_belongs_to_company",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if CarOperation.objects.filter(
            status__in=[
                CarOperation.OperationStatus.PENDING,
                CarOperation.OperationStatus.IN_PROGRESS,
            ],
            car=car,
        ).exists():
            raise CustomValidationError(
                message="السيارة قيد عمليه اخرى",
                code="car_in_progress",
                errors=[],
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not car.is_available_today():
            raise CustomValidationError(
                message="السيبارة غير مصرح لها هذا اليوم",
                code="car_not_active",
                errors=[],
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if service_type == "petrol":
            car_service = car.service
            liter_cost = (
                car_service.cost * company_branch.fees / 100
            ) + car_service.cost
            if car.balance < liter_cost:
                raise CustomValidationError(
                    message="السيارة لا تمتلك كافٍ من المال",
                    code="not_enough_balance",
                    errors=[],
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            liters_count = (
                car.permitted_fuel_amount
                if car.permitted_fuel_amount
                else car.tank_capacity
            )
            available_liters = math.floor(car.balance / liter_cost)
            available_liters = min(liters_count, available_liters)
            available_cost = available_liters * liter_cost
            if (
                CarOperation.objects.filter(
                    status=CarOperation.OperationStatus.COMPLETED,
                    car=car,
                    created__date=timezone.now().date(),
                ).count()
                > car.number_of_fuelings_per_day
            ):
                raise CustomValidationError(
                    message="السيارة تجاوزت عدد عمليات البترولية اليومية المسموح بها",
                    code="car_in_progress",
                    errors=[],
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        else:
            car_service = None
            available_liters = 0
            liter_cost = 0
            available_cost = car.balance

        station_branch = request.user.worker.station_branch
        car_operation = CarOperation.objects.create(
            car=car,
            driver=driver,
            service=car_service,
            worker_id=request.user.id,
            station_branch_id=station_branch.id,
            status=CarOperation.OperationStatus.PENDING,
            created_by_id=request.user.id,
        )

        car.is_blocked_balance_update = True
        car.save()

        return Response(
            {
                "message": "تم التحقق من السائق بنجاح",
                "car": {
                    "plate_number": car.plate_number,
                    "plate_character": car.plate_character,
                    "plate_color": COLOR_CHOICES_HEX.get(car.plate_color),
                    "fuel_type": car.fuel_type,
                    "liter_count": available_liters,
                    "cost": available_cost,
                    "code": car.code,
                    "service": {
                        "name": car_service.name if car_service else "-",
                    },
                },
                "operation_id": car_operation.id,
            },
            status=status.HTTP_200_OK,
        )
