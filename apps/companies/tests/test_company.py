import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.geo.models import City, Country, District
from apps.users.models import User


@pytest.mark.django_db
class TestCompany:
    def test_list_companies_success(self):
        url = reverse("companies-list")
        admin = User.objects.create(
            role=User.UserRoles.Admin,
            email="admin@gmail.com",
            name="admin",
            phone_number="123456789",
        )
        admin.set_password("admin")
        admin.save()
        access_token = AccessToken.for_user(admin)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = client.get(url)
        assert response.status_code == 200

    def test_list_companies_with_district_filter(self):
        admin = User.objects.create(
            role=User.UserRoles.Admin,
            email="admin@gmail.com",
            name="admin",
            phone_number="123456789",
        )
        admin.set_password("admin")
        admin.save()
        access_token = AccessToken.for_user(admin)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        egypt_country = Country.objects.create(name="Egypt", code="EGP")
        city = City.objects.create(name="Assuit", country_id=egypt_country.id)
        district = District.objects.create(name="Cairo", city=city)
        url = reverse("companies-list")
        response = client.get(url, {"district": district.id})
        assert response.status_code == 200

    def test_list_company_with_district_filter_falied(self):
        pass
