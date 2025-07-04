from django.contrib.auth.hashers import make_password
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.shared.base_exception_class import CustomValidationError
from apps.stations.api.v1.serializers import (
    ListStationSerializer,
    SingleStationBranchSerializer,
    StationBranchWithDistrictSerializer,
)
from apps.stations.models.stations_models import StationBranch
from apps.users.models import StationOwner, User, Worker


class SingleWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ["id", "name", "phone_number"]


class ListWorkerSerializer(serializers.ModelSerializer):
    station_branch = SingleStationBranchSerializer()

    class Meta:
        model = Worker
        fields = ["id", "name", "phone_number", "station_branch"]


@extend_schema_serializer(exclude_fields=["email"])
class CreateWorkerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    station_branch = serializers.PrimaryKeyRelatedField(
        queryset=StationBranch.objects.all(), required=True, allow_null=False
    )
    phone_number = serializers.CharField(
        error_messages={"unique": "هذا الرقم موجود بالفعل"}
    )

    def validate_phone_number(self, phone_number):
        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError("هذا الرقم موجود بالفعل.")
        return phone_number

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")

        return attrs

    class Meta:
        model = Worker
        fields = [
            "id",
            "name",
            "phone_number",
            "email",
            "station_branch",
            "password",
            "confirm_password",
        ]

    def create(self, validated_data):
        validated_data["role"] = User.UserRoles.StationWorker
        validated_data["email"] = validated_data.get(
            "email", validated_data["phone_number"] + "@petro.com"
        )
        validated_data["password"] = make_password(validated_data["password"])
        validated_data.pop("confirm_password")
        # check station branch related to station
        if (
            validated_data["station_branch"].station_id
            != self.context["request"].station_id
        ):
            raise CustomValidationError(
                message="Station branch not related to your station."
            )
        return Worker.objects.create(**validated_data)


class UpdateWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ["id", "name", "phone_number", "password", "confirm_password"]

    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if "password" in attrs:
            if "confirm_password" not in attrs:
                raise serializers.ValidationError("Confirm password is required.")
            if attrs["password"] != attrs["confirm_password"]:
                raise serializers.ValidationError("Passwords do not match.")
        return attrs

    def update(self, instance, validated_data):
        if "password" in validated_data:
            validated_data["password"] = make_password(validated_data["password"])
            validated_data.pop("confirm_password", None)
        return super().update(instance, validated_data)


class WorkerWithBranchSerializer(serializers.ModelSerializer):
    station_branch = StationBranchWithDistrictSerializer()

    class Meta:
        model = Worker
        fields = ["id", "name", "phone_number", "station_branch"]

    def get_station_branch(self, obj):
        return obj.station_branch.name


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


@extend_schema_serializer(exclude_fields=["email"])
class StationBranchManagerCreationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = StationOwner
        fields = ["id", "name", "phone_number", "email", "password", "confirm_password"]

    def create(self, validated_data):
        validated_data["role"] = User.UserRoles.StationBranchManager
        validated_data["email"] = validated_data.get(
            "email", validated_data["phone_number"] + "@petro.com"
        )
        if "password" not in validated_data:
            raise serializers.ValidationError("كلمة المرور مطلوبة.")
        if "confirm_password" not in validated_data:
            raise serializers.ValidationError("تاكيد كلمة المرور مطلوب.")
        if validated_data["password"] != validated_data.get("confirm_password"):
            raise serializers.ValidationError("كلمتا المرور غير متطابقة.")
        validated_data["password"] = make_password(validated_data["password"])
        validated_data.pop("confirm_password")
        validated_data["station_id"] = self.context["request"].station_id
        return StationOwner.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if "password" in validated_data:
            if "confirm_password" not in validated_data:
                raise CustomValidationError(
                    message="تاكيد كلمة المرور مطلوب.",
                    code="invalid",
                    errors=[],
                )
            if validated_data["password"] != validated_data.get("confirm_password"):
                raise CustomValidationError(
                    message="كلمتا المرور غير متطابقة.",
                    code="invalid",
                    errors=[],
                )
            validated_data["password"] = make_password(validated_data["password"])
            validated_data.pop("confirm_password")
        return super().update(instance, validated_data)
