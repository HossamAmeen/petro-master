import pytest
from django.test import Client
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken

from apps.stations.models.stations_models import Station
from apps.users.models import StationOwner, User


@pytest.mark.django_db
class TestUserAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = Client()
        self.user = User.objects.create(name="user1", phone_number="011020",
                                        email="user1@gmail.com", password="user1", role="admin")
        self.station = Station.objects.create(
            name="station1", address="location1", lang="3.77",
            lat="4.99", created_by=self.user, updated_by=self.user)
        self.station_owner = StationOwner.objects.create(
            name="owner1", phone_number="01000005693", email="owner1@gmail.com",
            password="owner1", created_by=self.user, updated_by=self.user, station=self.station)
        access_token = AccessToken.for_user(self.station_owner)
        self.client.defaults['HTTP_AUTHORIZATION'] = \
            f'Bearer {str(access_token)}'
        self.url_list = reverse("station-owners-list")
        self.url_detail = reverse("station-owners-detail", args=[self.station_owner.id])

    def test_list_station_owner(self):
        response = self.client.get(self.url_list)
        assert response.status_code == 200

    def test_create_station_owner(self):
        data = {'name': "owner2", 'phone_number': "0100055", 'email': "owner2@gmail.com",
                'password': "owner1", 'created_by': self.user.id,
                'updated_by': self.user.id, 'station': self.station.id}
        response = self.client.post(
            self.url_list,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201

    def test_update_station_owner(self):
        update_data = {'name': "owner3", 'phone_number': "0100055",
                       'email': "owner3@gmail.com", 'password': "owner1",
                       'created_by': self.user.id, 'updated_by': self.user.id,
                       'station': self.station.id}
        response = self.client.put(
            self.url_detail,
            data=update_data,
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_retrieve_station_owner(self):
        update_data = {'name': "owner2", 'phone_number': "0100055",
                       'email': "owner2@gmail.com", 'password': "owner1",
                       'created_by': self.user.id, 'updated_by': self.user.id,
                       'station': self.station.id}
        response = self.client.get(
            self.url_detail,
            data=update_data,
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_delete_station_owner(self):
        response = self.client.delete(self.url_detail)
        assert response.status_code == 204

    def test_filter_station_owner_by_station(self):
        response = self.client.get(self.url_list, {'station': self.station.id})
        assert response.status_code == 200
        assert all(owner['station']['id'] == self.station.id for owner in response.data['results'])

    def test_search_station_owner_by_name(self):
        response = self.client.get(self.url_list, {'search': 'owner1'})
        assert response.status_code == 200
        assert any(owner['name'] == 'owner1' for owner in response.data['results'])

    def test_search_station_owner_by_phone_number(self):
        response = self.client.get(self.url_list, {'search': '01000005693'})
        assert response.status_code == 200
        assert any(owner['phone_number'] == '01000005693' for owner in response.data['results'])

    def test_search_station_owner_by_email(self):
        response = self.client.get(self.url_list, {'search': 'owner1@gmail.com'})
        assert response.status_code == 200
        assert any(owner['email'] == 'owner1@gmail.com' for owner in response.data['results'])
