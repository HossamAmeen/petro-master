from django.urls import path

from .views import (
    CompanyLoginAPIView,
    DashboardLoginAPIView,
    PasswordResetConfirmAPIView,
    PasswordResetRequestAPIView,
    ProfileAPIView,
    StationLoginAPIView,
)

urlpatterns = [
    path("company/login/", CompanyLoginAPIView.as_view(), name="company_login"),
    path("station/login/", StationLoginAPIView.as_view(), name="station_login"),
    path("dashboard/login/", DashboardLoginAPIView.as_view(), name="dashboard_login"),
    path("profile/", ProfileAPIView.as_view(), name="profile"),
    path(
        "password-reset-request/",
        PasswordResetRequestAPIView.as_view(),
        name="password_reset_request",
    ),
    path(
        "password-reset-confirm/<str:token>/",
        PasswordResetConfirmAPIView.as_view(),
        name="password_reset_confirm",
    ),
]
