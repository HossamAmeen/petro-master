import math
from datetime import timedelta
from decimal import Decimal

from django.db.transaction import atomic
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting.helpers import (
    generate_company_transaction,
    generate_station_transaction,
)
from apps.accounting.models import KhaznaTransaction
from apps.companies.models.operation_model import CarOperation
from apps.notifications.models import Notification
from apps.shared.base_exception_class import CustomValidationError
from apps.stations.api.station_serializers.car_operation_serializer import (
    updateStationGasCarOperationSerializer,
    updateStationOtherCarOperationSerializer,
)
from apps.stations.models.service_models import Service
from apps.users.models import CompanyUser, StationOwner


class StationGasOperationAPIView(APIView):
    @extend_schema(
        request=updateStationGasCarOperationSerializer,
        responses={200: updateStationGasCarOperationSerializer},
    )
    @atomic
    def patch(self, request, pk, *args, **kwargs):
        car_opertion = CarOperation.objects.filter(
            id=pk,
            status__in=[
                CarOperation.OperationStatus.PENDING,
                CarOperation.OperationStatus.IN_PROGRESS,
            ],
        ).first()
        if not car_opertion:
            raise CustomValidationError(
                {"error": "هذا العمليه غير موجوده او انتهت بالفعل"},
                code="not_found",
            )
        serializer = updateStationGasCarOperationSerializer(
            car_opertion, data=request.data, partial=True
        )
        if serializer.is_valid():
            status = CarOperation.OperationStatus.PENDING
            if "car_meter" in serializer.validated_data:
                if serializer.validated_data["car_meter"] < car_opertion.car.last_meter:
                    raise CustomValidationError(
                        {"error": "العداد الحالي يجب ان يكون اكبر من العداد السابق"},
                        code="not_found",
                    )
                status = CarOperation.OperationStatus.IN_PROGRESS
                serializer.save(status=status)

            elif "amount" in serializer.validated_data:
                if not car_opertion.start_time:
                    raise CustomValidationError(
                        {"error": "يجب تحديد الوقت البدء"},
                        code="not_found",
                    )
                end_time = timezone.localtime()
                if end_time > car_opertion.start_time + timedelta(seconds=70):
                    raise CustomValidationError(
                        {"error": "الوقت الانتهاء يجب ان يكون اقل من 60 ثانية"},
                        code="not_found",
                    )
                car = car_opertion.car
                car_tank_capacity = (
                    car.permitted_fuel_amount
                    if car.permitted_fuel_amount
                    else car.tank_capacity
                )
                company_liter_cost = (
                    car_opertion.service.cost * (car.branch.fees / 100)
                    + car_opertion.service.cost
                )
                available_liters = math.floor(car.balance / company_liter_cost)
                available_liters = min(car_tank_capacity, available_liters)
                if serializer.validated_data["amount"] > available_liters:
                    raise CustomValidationError(
                        {"error": "الكمية المطلوبة اكبر من الحد الأقصى"},
                        code="not_found",
                    )

                status = CarOperation.OperationStatus.COMPLETED
                duration = (end_time - car_opertion.created).total_seconds()
                cost = round(
                    Decimal(serializer.validated_data["amount"])
                    * Decimal(car_opertion.service.cost),
                    2,
                )
                company_cost = round(
                    Decimal(serializer.validated_data["amount"])
                    * Decimal(company_liter_cost),
                    2,
                )
                worker = car_opertion.worker
                station_cost = round(
                    Decimal(serializer.validated_data["amount"])
                    * Decimal(car_opertion.service.cost + worker.station_branch.fees),
                    2,
                )
                profits = round(company_cost - station_cost, 2)

                if car.is_with_odometer:
                    car.fuel_consumption_rate = (
                        car_opertion.car_meter - car.last_meter
                    ) / serializer.validated_data["amount"]

                serializer.save(
                    end_time=end_time,
                    status=status,
                    duration=duration,
                    cost=cost,
                    car_first_meter=car.last_meter,
                    company_cost=company_cost,
                    station_cost=station_cost,
                    profits=profits,
                    unit=Service.ServiceUnit.LITRE,
                    fuel_consumption_rate=car.fuel_consumption_rate,
                )

                car.is_blocked_balance_update = False
                car.last_meter = car_opertion.car_meter
                car.balance = car.balance - company_cost
                car.save()

                station_id = request.station_id
                generate_station_transaction(
                    station_id=station_id,
                    station_branch_id=worker.station_branch_id,
                    amount=station_cost,
                    status=KhaznaTransaction.TransactionStatus.APPROVED,
                    description=f"تم تفويل سيارة رقم {car.plate} بعدد {car_opertion.amount} لتر",
                    created_by_id=request.user.id,
                    is_internal=False,
                )
                station_branch = worker.station_branch
                station_branch.balance = station_branch.balance - station_cost
                station_branch.save()

                # send notifications for station users
                message = f"تم تفويل سيارة رقم {car_opertion.car.plate} بعدد {car_opertion.amount} لتر"
                notification_users = list(
                    StationOwner.objects.filter(station_id=station_id).values_list(
                        "id", flat=True
                    )
                )
                notification_users.append(request.user.id)
                for user_id in notification_users:
                    Notification.objects.create(
                        user_id=user_id,
                        title=message,
                        description=message,
                        type=Notification.NotificationType.MONEY,
                    )

                # send notfication for company user
                company_id = car.branch.company_id
                generate_company_transaction(
                    company_id=company_id,
                    amount=company_cost,
                    status=KhaznaTransaction.TransactionStatus.APPROVED,
                    description=f"تم تفويل سيارة رقم {car_opertion.car.plate} بعدد {car_opertion.amount} لتر",
                    created_by_id=request.user.id,
                    is_internal=True,
                )
                message = (
                    f"تم تفويل سيارة رقم {car_opertion.car.plate} بعدد {car_opertion.amount} لتر "
                    f"وخصم مبلغ بمقدار {car_opertion.company_cost:.2f} جنية"  # noqa
                )
                notification_users = list(
                    CompanyUser.objects.filter(company_id=company_id).values_list(
                        "id", flat=True
                    )
                )
                notification_users.append(request.user.id)
                for user_id in notification_users:
                    Notification.objects.create(
                        user_id=user_id,
                        title=message,
                        description=message,
                        type=Notification.NotificationType.MONEY,
                    )

                return Response(serializer.data)
            elif "start_time" in serializer.validated_data:
                car_opertion.start_time = timezone.localtime()
                car_opertion.save()
            return Response(serializer.data)

        raise CustomValidationError(serializer.errors)

    @atomic
    def delete(self, request, pk, *args, **kwargs):
        car_opertion = CarOperation.objects.filter(
            id=pk,
            status__in=[
                CarOperation.OperationStatus.PENDING,
                CarOperation.OperationStatus.IN_PROGRESS,
            ],
        ).first()
        if not car_opertion:
            raise CustomValidationError(
                {"error": "هذا العمليه غير موجوده او انتهت بالفعل"},
                code="not_found",
            )
        car_opertion.delete()
        car = car_opertion.car
        car.is_blocked_balance_update = False
        car.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StationOtherOperationAPIView(APIView):
    @extend_schema(
        request=updateStationOtherCarOperationSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                    },
                },
                description="",
            )
        },
    )
    @atomic
    def patch(self, request, pk, *args, **kwargs):
        car_operation = CarOperation.objects.filter(
            id=pk,
            status__in=[
                CarOperation.OperationStatus.PENDING,
                CarOperation.OperationStatus.IN_PROGRESS,
            ],
            worker_id=request.user.id,
            service__isnull=True,
        ).first()
        if not car_operation:
            raise CustomValidationError(
                {
                    "error": " هذا العمليه غير موجوده او انتهت بالفعل او لا يوجد بها خدمه محدده"
                },
                code="not_found",
            )
        station_branch = request.user.worker.station_branch
        serializer = updateStationOtherCarOperationSerializer(
            car_operation,
            data=request.data,
            context={"station_branch_id": station_branch.id},
        )
        if serializer.is_valid():
            serializer.save(status=CarOperation.OperationStatus.COMPLETED)
            car = car_operation.car
            company_branch = car.branch
            company_cost = (
                serializer.validated_data["cost"]
                * company_branch.other_service_fees
                / 100
            ) + serializer.validated_data["cost"]
            if car.balance < company_cost:
                raise CustomValidationError(
                    {"error": "السيارة لا تمتلك كافٍ من المال"},
                    code="not_enough_balance",
                    errors=[],
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            car.is_blocked_balance_update = False
            car.balance = car.balance - company_cost
            car.save()

            station_cost = serializer.validated_data["cost"] - (
                serializer.validated_data["cost"]
                * station_branch.other_service_fees
                / 100
            )
            generate_station_transaction(
                station_id=station_branch.station_id,
                station_branch_id=station_branch.id,
                amount=station_cost,
                status=KhaznaTransaction.TransactionStatus.APPROVED,
                description="تم اضافة الخدمه بنجاح الي السيارة رقم {car.plate}",
                created_by_id=request.user.id,
                is_internal=False,
            )
            # send notifications for station users
            message = f"تم اضافة الخدمه {serializer.data['service_name']} بنجاح الي السيارة رقم {car.plate} بقيمة {station_cost:.2f} جنية"  # noqa
            notification_users = list(
                StationOwner.objects.filter(
                    station_id=station_branch.station_id
                ).values_list("id", flat=True)
            )
            notification_users.append(request.user.id)
            for user_id in notification_users:
                Notification.objects.create(
                    user_id=user_id,
                    title=message,
                    description=message,
                    type=Notification.NotificationType.MONEY,
                )
            # send notfication for company user
            company_id = company_branch.company_id
            generate_company_transaction(
                company_id=company_id,
                amount=company_cost,
                status=KhaznaTransaction.TransactionStatus.APPROVED,
                description=f"تم اضافة الخدمه {serializer.data['service_name']} بنجاح الي السيارة رقم {car.plate}",
                created_by_id=request.user.id,
                is_internal=False,
            )
            message = f"تم اضافة الخدمه {serializer.data['service_name']} بنجاح الي السيارة رقم {car.plate} بقيمة {company_cost:.2f} جنية"  # noqa
            notification_users = list(
                CompanyUser.objects.filter(company_id=company_id).values_list(
                    "id", flat=True
                )
            )
            notification_users.append(request.user.id)
            for user_id in notification_users:
                Notification.objects.create(
                    user_id=user_id,
                    title=message,
                    description=message,
                    type=Notification.NotificationType.MONEY,
                )
            return Response({"message": "تم اضافة الخدمه بنجاح"})
        raise CustomValidationError(serializer.errors)

    def delete(self, request, pk, *args, **kwargs):
        car_opertion = CarOperation.objects.filter(
            id=pk,
            status__in=[
                CarOperation.OperationStatus.PENDING,
                CarOperation.OperationStatus.IN_PROGRESS,
            ],
            worker_id=request.user.id,
            service__isnull=True,
        ).first()
        if not car_opertion:
            raise CustomValidationError(
                {
                    "error": " هذا العمليه غير موجوده او انتهت بالفعل او لا يوجد بها خدمه محدده"
                },
                code="not_found",
            )
        car_opertion.delete()

        car = car_opertion.car
        car.is_blocked_balance_update = False
        car.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
