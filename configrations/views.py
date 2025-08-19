from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from configrations.serializers import SliderSerializer

from .models import ConfigrationsModel, Slider


class ConfigrationsView(APIView):
    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "term_conditions": {"type": "string"},
                    "privacy_policy": {"type": "string"},
                    "about_us": {"type": "string"},
                    "faq": {"type": "string"},
                },
            }
        }
    )
    def get(self, request):
        configrations = ConfigrationsModel.objects.first()
        if not configrations:
            return Response(
                {"term_conditions": "", "privacy_policy": "", "about_us": "", "faq": ""}
            )

        return Response(
            {
                "term_conditions": configrations.term_conditions,
                "privacy_policy": configrations.privacy_policy,
                "about_us": configrations.about_us,
                "faq": configrations.faq,
                "app_version": configrations.app_version,
                "company_support_email": configrations.company_support_email,
                "company_support_phone": configrations.company_support_phone,
                "company_support_address": configrations.company_support_address,
                "company_support_name": configrations.company_support_name,
                "station_support_email": configrations.station_support_email,
                "station_support_phone": configrations.station_support_phone,
                "station_support_address": configrations.station_support_address,
                "station_support_name": configrations.station_support_name,
            }
        )


class SliderView(ListAPIView):
    queryset = Slider.objects.filter()
    serializer_class = SliderSerializer
