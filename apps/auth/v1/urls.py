from django.urls import path

from .views import CompanyLoginAPIView, ProfileAPIView

urlpatterns = [
    path('company/login/', CompanyLoginAPIView.as_view(), name='company_login'),
    path('profile/', ProfileAPIView.as_view(), name='profile'),
]
