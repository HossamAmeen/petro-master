from rest_framework import serializers

from apps.geo.models import City, District


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = "__all__"


class CityNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["name"]


class ListDistrictSerializer(serializers.ModelSerializer):
    city = CitySerializer()

    class Meta:
        model = District
        fields = "__all__"


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = "__all__"


class DistrictWithcitynameSerializer(serializers.ModelSerializer):
    city = CityNameSerializer()

    class Meta:
        model = District
        fields = ["id", "name", "city"]
