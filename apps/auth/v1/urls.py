from django.urls import path

from .views import CompanyLoginAPIView

urlpatterns = [
    path('company/login/', CompanyLoginAPIView.as_view(), name='company_login'),
]
