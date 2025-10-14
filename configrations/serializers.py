from rest_framework import serializers

from configrations.models import ConfigrationsModel, Slider


class SliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slider
        fields = "__all__"


class ConfigrationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigrationsModel
        fields = "__all__"


class ContactUsSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    message = serializers.CharField()
