from django.utils.timezone import now
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models.operation_model import CarOperation
from apps.shared.base_exception_class import CustomValidationError
from apps.stations.api.station_serializers.car_operation_serializer import (
    updateCarOperationSerializer,
)
from apps.stations.models.service_models import Service


class StationGasOperationsAPIView(APIView):
    @extend_schema(
        request=updateCarOperationSerializer,
        responses={200: updateCarOperationSerializer},
    )
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
        serializer = updateCarOperationSerializer(
            car_opertion, data=request.data, partial=True
        )
        if serializer.is_valid():
            status = CarOperation.OperationStatus.PENDING
            if "car_meter" in serializer.validated_data:
                status = CarOperation.OperationStatus.IN_PROGRESS
                serializer.save(status=status)
            elif "amount" in serializer.validated_data:
                status = CarOperation.OperationStatus.COMPLETED
                end_time = now()
                duration = end_time - car_opertion.start_time
                cost = serializer.validated_data["amount"] * car_opertion.service.cost
                company_cost = serializer.validated_data["amount"] * (
                    car_opertion.service.cost + car_opertion.car.branch.fees
                )
                station_cost = serializer.validated_data["amount"] * (
                    car_opertion.service.station_cost + car_opertion.worker.branch.fees
                )
                profits = company_cost - station_cost
                serializer.save(
                    end_time=end_time,
                    status=status,
                    duration=duration,
                    cost=cost,
                    company_cost=company_cost,
                    station_cost=station_cost,
                    profits=profits,
                    unit=Service.ServiceUnit.LITRE,
                )

                return Response(serializer.data)

            else:
                serializer.save()
            return Response(serializer.data)

        raise CustomValidationError(serializer.errors)
