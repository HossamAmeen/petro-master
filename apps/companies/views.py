from rest_framework import viewsets

from apps.shared.mixins.inject_user_mixins import InjectUserMixin

from .models import Driver
from .serializers import DriverSerializer, ListDriverSerializer


class DriverViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = Driver.objects.select_related('branch__district').order_by('-id')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ListDriverSerializer
        return DriverSerializer
