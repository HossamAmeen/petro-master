from rest_framework import serializers


class BalanceUpdateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    type = serializers.ChoiceField(
        choices=[("add", "add"), ("subtract", "subtract")], required=True
    )
