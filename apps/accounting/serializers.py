from rest_framework import serializers
from .models import KhaznaTransaction


class KhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = KhaznaTransaction
        fields = '__all__'
