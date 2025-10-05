from django.core.validators import MinValueValidator
from rest_framework import serializers

from apps.geo.v1.serializers import DistrictWithcitynameSerializer
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import Station, StationBranch, StationService
from apps.users.models import StationOwner


class ListServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "unit", "type", "cost", "image"]


class ServiceNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Service
        fields = ["id", "name"]


class SingleStationServiceSerializer(serializers.ModelSerializer):
    service = ServiceNameSerializer()

    class Meta:
        model = StationService
        fields = ["id", "service"]


class ListStationSerializer(serializers.ModelSerializer):
    district = DistrictWithcitynameSerializer()
    branches_count = serializers.IntegerField()
    services_count = serializers.IntegerField()
    managers_count = serializers.IntegerField()
    workers_count = serializers.IntegerField()
    total_balance = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Station
        fields = "__all__"


class StationNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ["id", "name"]


class SingleStationBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationBranch
        fields = ["id", "name", "address", "district", "station"]


class StationBranchWithDistrictSerializer(serializers.ModelSerializer):
    district = DistrictWithcitynameSerializer()

    class Meta:
        model = StationBranch
        fields = ["id", "name", "address", "district", "station"]


class ListStationBranchSerializer(serializers.ModelSerializer):
    services = serializers.SerializerMethodField()
    district = DistrictWithcitynameSerializer()
    station = StationNameSerializer()
    managers_count = serializers.IntegerField()

    class Meta:
        model = StationBranch
        fields = "__all__"

    def get_services(self, instance):
        services = Service.objects.filter(
            station_branch_services__station_branch=instance
        ).values("id", "name")
        return list(services)


class ListStationBranchForDashboardSerializer(serializers.ModelSerializer):
    district = DistrictWithcitynameSerializer()
    station = StationNameSerializer()
    managers_count = serializers.IntegerField()
    services_count = serializers.IntegerField()
    workers_count = serializers.IntegerField()
    total_balance = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = StationBranch
        fields = "__all__"


class ListStationBranchForLandingpageSerializer(serializers.ModelSerializer):
    district = DistrictWithcitynameSerializer()
    station = StationNameSerializer()

    class Meta:
        model = StationBranch
        fields = ["id", "name", "address", "district", "station"]


class UpdateStationBranchBalanceSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[("add", "Add"), ("subtract", "Subtract")])
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(10)]
    )


class AssignServicesSerializer(serializers.Serializer):
    services = serializers.ListField(child=serializers.IntegerField())


class StationBranchAssignManagersSerializer(serializers.Serializer):
    managers = serializers.ListField(child=serializers.IntegerField())

    def validate(self, attrs):
        manager_ids = attrs["managers"]

        # Get valid users from the same company
        valid_managers = StationOwner.objects.filter(
            station_id=self.context["request"].station_id,
            id__in=manager_ids,
        ).values_list("id", flat=True)

        invalid_ids = set(manager_ids) - set(valid_managers)
        if invalid_ids:
            raise serializers.ValidationError(
                {
                    "message": f"بعض المديرين لا ينتمون لمحطتك (المديرين غير الصالحة: {invalid_ids})",  # noqa
                    "errors": {"invalid_manager_ids": list(invalid_ids)},
                }
            )

        return attrs
