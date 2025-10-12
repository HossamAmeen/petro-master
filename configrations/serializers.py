from rest_framework.serializers import ModelSerializer

from configrations.models import ConfigrationsModel, Slider


class SliderSerializer(ModelSerializer):
    class Meta:
        model = Slider
        fields = "__all__"


class ConfigrationsSerializer(ModelSerializer):
    class Meta:
        model = ConfigrationsModel
        fields = "__all__"
