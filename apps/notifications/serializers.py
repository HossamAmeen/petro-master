from rest_framework import serializers

from apps.notifications.models import Notification
from apps.users.serializers import UserSerializer


class ListNotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Notification
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = '__all__'
