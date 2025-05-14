from rest_framework import serializers

from apps.stations.models.stations_models import StationBranch
from apps.stations.v1.serializers import ListStationSerializer
from apps.users.models import StationOwner, Worker


class SingleWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ["id", "name", "phone_number"]


class StationOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationOwner
        fields = "__all__"


class ListStationOwnerSerializer(serializers.ModelSerializer):
    station = ListStationSerializer()

    class Meta:
        model = StationOwner
        fields = "__all__"


class StationBranchSerializer(serializers.ModelSerializer):

    class Meta:
        model = StationBranch
        fields = "__all__"


class ListStationBranchManagerSerializer(serializers.ModelSerializer):
    station_branches = serializers.SerializerMethodField()

    class Meta:
        model = StationOwner
        fields = ["id", "name", "phone_number", "email", "station", "station_branches"]

    def get_station_branches(self, obj):
        return StationBranchSerializer(
            StationBranch.objects.filter(managers__user=obj), many=True
        ).data
