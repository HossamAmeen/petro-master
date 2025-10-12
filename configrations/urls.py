from django.urls import path

from .views import ConfigrationsView, SliderView, StatisticsViewSet

urlpatterns = [
    path("configrations", ConfigrationsView.as_view(), name="configrations"),
    path("silders/", SliderView.as_view(), name="sliders"),
    path("statistics/", StatisticsViewSet.as_view({"get": "list"}), name="statistics"),
]
