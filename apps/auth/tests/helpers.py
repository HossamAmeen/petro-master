from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

LOGIN_PASSWORD = "password123"


def company_login_url():
    return reverse("company_login")


def station_login_url():
    return reverse("station_login")


def dashboard_login_url():
    return reverse("dashboard_login")


def profile_url():
    return reverse("profile")


def password_reset_request_url():
    return reverse("password_reset_request")


def password_reset_confirm_url(token):
    return reverse("password_reset_confirm", kwargs={"token": token})


def token_refresh_url():
    return reverse("token_refresh")


def set_login_password(user, password=LOGIN_PASSWORD):
    user.set_password(password)
    user.save(update_fields=["password"])
    return user


def login_identifier(user):
    return user.email or user.phone_number


def login_payload(user, *, identifier=None, password=LOGIN_PASSWORD):
    return {
        "identifier": identifier if identifier is not None else login_identifier(user),
        "password": password,
    }


def company_refresh_for(user, company_id):
    refresh = RefreshToken.for_user(user)
    refresh["user_name"] = user.name
    refresh["role"] = user.role
    refresh["company_id"] = company_id
    return refresh


def station_refresh_for(user, station_id):
    refresh = RefreshToken.for_user(user)
    refresh["user_name"] = user.name
    refresh["role"] = user.role
    refresh["station_id"] = station_id
    return refresh


def decode_access(token):
    return AccessToken(token)


def decode_refresh(token):
    return RefreshToken(token)
