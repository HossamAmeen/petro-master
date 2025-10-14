from django.urls import path

from .views import ConfigrationsView, ContactUsView, SliderView, StatisticsViewSet

urlpatterns = [
    path("configrations", ConfigrationsView.as_view(), name="configrations"),
    path("silders/", SliderView.as_view(), name="sliders"),
    path("statistics/", StatisticsViewSet.as_view({"get": "list"}), name="statistics"),
    path("contact-us/", ContactUsView.as_view(), name="contact-us"),
]
