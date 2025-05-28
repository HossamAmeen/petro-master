from django.test import Client
from django.urls import reverse


class TestCompany:
    def test_list_companies_success(self):
        url = reverse("companies-list")
        client = Client()
        response = client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 0
