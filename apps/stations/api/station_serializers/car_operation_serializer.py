from rest_framework import serializers

from apps.shared.base_exception_class import CustomValidationError


class updateStationGasCarOperationSerializer(serializers.Serializer):
    car_meter = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    motor_image = serializers.ImageField(required=False)
    fuel_image = serializers.ImageField(required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    start_time = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if "amount" in attrs and attrs["amount"] <= 0:
            raise CustomValidationError({"amount": "الكمية يجب ان تكون اكبر من 0"})
        if "car_meter" in attrs:
            if "motor_image" not in attrs:
                raise CustomValidationError(
                    {"motor_image": "يجب ارفاق صورة لعداد السيارة"}
                )
            if attrs["car_meter"] < 0:
                raise CustomValidationError(
                    {"car_meter": "يجب ان يكون العداد اكبر من 0"}
                )
        if "amount" in attrs and "fuel_image" not in attrs:
            raise CustomValidationError({"fuel_image": "يجب ارفاق صورة لمضخه الوقود"})
        return attrs

    def update(self, instance, validated_data):
        instance.car_meter = validated_data.get("car_meter", instance.car_meter)
        instance.motor_image = validated_data.get("motor_image", instance.motor_image)
        instance.fuel_image = validated_data.get("fuel_image", instance.fuel_image)
        instance.amount = validated_data.get("amount", instance.amount)
        instance.status = validated_data.get("status", instance.status)
        instance.save()

        return instance


class updateStationOtherCarOperationSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    start_time = serializers.DateTimeField(required=False, allow_null=True)
