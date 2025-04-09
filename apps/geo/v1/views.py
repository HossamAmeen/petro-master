from rest_framework import viewsets

from apps.geo.models import City, District
from apps.geo.v1.serializers import CitySerializer, ListDistrictSerializer


class CityViewSet(viewsets.ModelViewSet):
    authentication_classes = []
    permission_classes = []
    queryset = City.objects.all()
    serializer_class = CitySerializer
    http_method_names = ["get"]


class DistrictViewSet(viewsets.ModelViewSet):
    authentication_classes = []
    permission_classes = []
    queryset = District.objects.select_related("city").order_by("-id")
    serializer_class = ListDistrictSerializer
    http_method_names = ["get"]
