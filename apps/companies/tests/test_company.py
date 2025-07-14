import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.companies.models.company_models import Company, CompanyBranch
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


@pytest.mark.django_db
class TestCompanyBranch:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.user = User.objects.create(
            name="user1",
            phone_number="011020",
            email="user1@gmail.com",
            password="user1",
            role="company_owner",
            is_staff=True,
        )
        self.country = Country.objects.create(name="Egypt", code="EG")
        self.city = City.objects.create(name="Cairo", country=self.country)
        self.district = District.objects.create(name="District1", city=self.city)
        self.company = Company.objects.create(
            name="company1",
            address="location1",
            balance=1000.00,
            district=self.district,
            created_by=self.user,
            updated_by=self.user,
        )
        self.company_branch = CompanyBranch.objects.create(
            name="branch1",
            address="location2",
            balance=500.00,
            company=self.company,
            district=self.district,
            created_by=self.user,
            updated_by=self.user,
        )

        access_token = AccessToken.for_user(self.user)
        access_token["company_id"] = self.company.id
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {str(access_token)}"
        self.url_list = reverse("company-branches-list")
        self.url_detail = reverse("company-branches-detail", args=[self.company_branch.id])

    def test_List_company_branch_success(self):
        response = self.client.get(self.url_list)
        assert response.status_code == 200
        data = response.data
        assert data["count"] == 1

        branch = data["results"][0]
        assert branch["name"] == "branch1"
        assert branch["address"] == "location2"
        assert float(branch["balance"]) == 500.00
        assert branch["district"]["id"] == self.district.id
        assert branch["company"]["name"] == self.company.name
