from rest_framework import viewsets

from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.users.models import User

from .serializers import ListUserSerializer, UserSerializer


class UserViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related('created_by', 'updated_by').order_by('-id')

    def get_serializer_class(self):
        if self.action == 'list':
            return ListUserSerializer
        return UserSerializer
