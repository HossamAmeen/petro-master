from django.urls import path

from .views import ConfigrationsView

urlpatterns = [
    path("configrations", ConfigrationsView.as_view(), name="configrations"),
]
