from rest_framework import serializers

from apps.stations.models import Station


class StationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Station
        fields = '__all__'
