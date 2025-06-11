from rest_framework import serializers

from apps.companies.models.company_models import Car, Driver
from apps.shared.base_exception_class import CustomValidationError


class AddCarGasOperationSerializer(serializers.Serializer):
    car_code = serializers.CharField()
    driver_code = serializers.CharField()

    def validate(self, attrs):
        car = Car.objects.filter(code=attrs["car_code"]).first()
        driver = Driver.objects.filter(code=attrs["driver_code"]).first()
        if not car:
            raise CustomValidationError({"car_code": "كود السيارة هذا غير صحيح"})
        if not driver:
            raise CustomValidationError({"driver_code": "كود السائق هذا غير صحيح"})
        if car.branch.company_id != driver.branch.company_id:
            raise CustomValidationError({"driver_code": "السائق لا ينتمي للشركة"})

        attrs["car"] = car
        attrs["driver"] = driver
        attrs["service"] = car.service
        return attrs
