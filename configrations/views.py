from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConfigrationsModel


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
            }
        )
