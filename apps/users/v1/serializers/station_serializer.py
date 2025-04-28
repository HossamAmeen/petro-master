from rest_framework import serializers

from apps.users.models import Worker


class SingleWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ["id", "name", "phone_number"]
