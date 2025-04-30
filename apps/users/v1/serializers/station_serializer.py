from rest_framework import serializers

from apps.stations.models.stations_models import Station
from apps.users.models import StationOwner, Worker


class SingleWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ["id", "name", "phone_number"]


class StationOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationOwner
        fields = '__all__'


class ListStationOwnerSerializer(serializers.ModelSerializer):
    station = Station()

    class Meta:
        model = StationOwner
        fields = '__all__'
