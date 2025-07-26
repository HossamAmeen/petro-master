from rest_framework import serializers

from apps.stations.models.stations_models import Station


class StationCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Station
        fields = ["name", "address", "lang", "lat", "district"]


class StationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ["name", "address", "lang", "lat", "district"]
