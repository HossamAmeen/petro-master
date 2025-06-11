from rest_framework import status
from rest_framework.views import APIView

from apps.companies.models.operation_model import CarOperation
from apps.shared.base_exception_class import CustomValidationError


class StationGasOperationsAPIView(APIView):
    def patch(self, request, *args, **kwargs):
        car_opertion = CarOperation.objects.filter(
            id=kwargs["pk"],
            status__in=[
                CarOperation.OperationStatus.PENDING,
                CarOperation.OperationStatus.IN_PROGRESS,
            ],
        ).first()
        if not car_opertion:
            raise CustomValidationError(
                {"error": "هذا العمليه غير موجوده او انتهت بالفعل"},
                status=status.HTTP_404_NOT_FOUND,
            )
