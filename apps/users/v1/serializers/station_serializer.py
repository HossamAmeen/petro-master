from rest_framework import serializers

from apps.stations.models.stations_models import StationBranch
from apps.stations.v1.serializers import (
    ListStationBranchSerializer,
    ListStationSerializer,
)
from apps.users.models import StationBranchManager, StationOwner, Worker
from apps.users.v1.serializers.user_serializers import UserSerializer


class SingleWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ["id", "name", "phone_number"]


class ListWorkerSerializer(serializers.ModelSerializer):
    station_branch = ListStationBranchSerializer()

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


class StationBranchManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationBranchManager
        fields = "__all__"


class StationBranchSerializer(serializers.ModelSerializer):

    class Meta:
        model = StationBranch
        fields = "_all_"


class ListStationBranchManagerSerializer(serializers.ModelSerializer):
    station_branch = StationBranchSerializer()
    user = UserSerializer()

    class Meta:
        model = StationBranchManager
        fields = "__all__"
