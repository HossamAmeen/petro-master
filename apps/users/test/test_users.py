import pytest
from django.test import Client
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.models import User


@pytest.mark.django_db
class TestAdminUserAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = Client()
        self.user = User.objects.create(name="user55", phone_number="01102055",
                                        email="user55@gmail.com", password="user1", role="admin")
        access_token = AccessToken.for_user(self.user)
        self.client.defaults['HTTP_AUTHORIZATION'] = \
            f'Bearer {str(access_token)}'
        self.url_list = reverse("users-list")
        self.url_detail = reverse("users-detail", args=[self.user.id])

    def test_list_user(self):
        response = self.client.get(self.url_list)
        assert response.status_code == 200

    def test_create_user(self):
        data = {'name': "user56", 'phone_number': "01102056",
                'email': "user56@gmail.com", 'password': "user1", 'role': "admin"}
        response = self.client.post(self.url_list, data=data, content_type="application/json")
        assert response.status_code == 201

    def test_retrieve_user(self):
        response = self.client.get(self.url_detail, content_type="application/json")
        assert response.status_code == 200

    def test_update_user(self):
        update_data = {'name': "user58", 'phone_number': "01102058", 'email': "user58@gmail.com", 'password': "user1", 'role': "admin"}
        response = self.client.patch(self.url_detail, data=update_data, content_type="application/json")
        assert response.status_code == 200

    def test_delete_user(self):
        response = self.client.delete(self.url_detail)
        assert response.status_code == 204
