from django.urls import path

from .views import ConfigrationsView, SliderView

urlpatterns = [
    path("configrations", ConfigrationsView.as_view(), name="configrations"),
    path("silders/", SliderView.as_view(), name="sliders"),
]
