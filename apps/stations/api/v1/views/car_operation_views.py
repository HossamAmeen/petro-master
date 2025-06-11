from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models.operation_model import CarOperation
from apps.shared.base_exception_class import CustomValidationError
from apps.stations.api.v1.car_operation_serializer import AddCarGasOperationSerializer


class AddCarGasOperationAPIView(APIView):
    def post(self, request):
        serializer = AddCarGasOperationSerializer(data=request.data)
        if serializer.is_valid():
            CarOperation.objects.create(
                car=serializer.validated_data["car"],
                driver=serializer.validated_data["driver"],
                service=serializer.validated_data["service"],
                worker_id=request.user.id,
                station_branch_id=request.user.worker.station_branch_id,
                fuel_type=serializer.validated_data["car"].fuel_type,
                unit=serializer.validated_data["service"].unit,
                status=CarOperation.OperationStatus.PENDING,
            )
            return Response({"message": "تم اضافة العمليه للسيارة بنجاح."})
        return CustomValidationError(serializer.errors)
