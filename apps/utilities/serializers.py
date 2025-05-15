from django.core.validators import MinValueValidator
from rest_framework import serializers


class BalanceUpdateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        validators=[MinValueValidator(1)],
    )
    type = serializers.ChoiceField(
        choices=[("add", "add"), ("subtract", "subtract")], required=True
    )


class ErrorDetailSerializer(serializers.ListSerializer):
    child = serializers.CharField()


class MessageErrorsSerializer(serializers.Serializer):
    message = serializers.CharField(read_only=True)
    validation_errors = serializers.DictField(
        child=ErrorDetailSerializer(), read_only=True
    )

    class Meta:
        ref_name = "MessageErrors"
