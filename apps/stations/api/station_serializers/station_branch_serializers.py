from rest_framework import serializers

from apps.stations.models.stations_models import StationBranch


class StationBranchCreationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationBranch
        fields = [
            "name",
            "address",
            "lang",
            "lat",
            "district",
            "station",
            "fees",
            "other_service_fees",
            "cash_request_fees",
        ]


class StationBranchUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationBranch
        fields = [
            "name",
            "address",
            "lang",
            "lat",
            "district",
            "station",
            "fees",
            "other_service_fees",
            "cash_request_fees",
        ]
