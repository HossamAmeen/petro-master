import pytest
from django.test import Client
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken

from apps.geo.models import City, Country, District
from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import StationBranchManager, StationOwner, User


@pytest.mark.django_db
class TestUserAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = Client()
        self.user = User.objects.create(
            name="user1",
            phone_number="011020",
            email="user1@gmail.com",
            password="user1",
            role="admin",
        )
        self.station = Station.objects.create(
            name="station1",
            address="location1",
            lang="3.77",
            lat="4.99",
            created_by=self.user,
            updated_by=self.user,
        )
        self.station_owner = StationOwner.objects.create(
            name="owner1",
            phone_number="01000005693",
            email="owner1@gmail.com",
            password="owner1",
            created_by=self.user,
            updated_by=self.user,
            station=self.station,
        )
        access_token = AccessToken.for_user(self.station_owner)
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {str(access_token)}"
        self.url_list = reverse("station-owners-list")
        self.url_detail = reverse("station-owners-detail", args=[self.station_owner.id])

    def test_list_station_owner(self):
        response = self.client.get(self.url_list)
        assert response.status_code == 200
        data = response.json()
        assert len(data['results']) == 1
        expected_data = [
            {
                'name': "owner1",
                'phone_number': "01000005693",
                'email': "owner1@gmail.com",
                'password': "owner1",
                'created_by': self.user.id,
                'updated_by': self.user.id,
                'station': self.station.id
            }
        ]

        sorted_results = sorted(data["results"], key=lambda x: x["name"])
        sorted_expected = sorted(expected_data, key=lambda x: x["name"])

        for actual, expected in zip(sorted_results, sorted_expected):
            assert actual["name"] == expected["name"]
            assert actual["email"] == expected["email"]
            assert actual["phone_number"] == expected["phone_number"]
            assert actual["password"] == expected["password"]
            assert actual["created_by"] == expected["created_by"]
            assert actual["updated_by"] == expected["updated_by"]

    def test_create_station_owner(self):
        data = {
            "name": "owner2",
            "phone_number": "0100055",
            "email": "owner2@gmail.com",
            "password": "owner1",
            "created_by": self.user.id,
            "updated_by": self.user.id,
            "station": self.station.id,
        }
        response = self.client.post(
            self.url_list, data=data, content_type="application/json"
        )
        assert response.status_code == 201

    def test_update_station_owner(self):
        update_data = {
            "name": "owner3",
            "phone_number": "0100055",
            "email": "owner3@gmail.com",
            "password": "owner1",
            "created_by": self.user.id,
            "updated_by": self.user.id,
            "station": self.station.id,
        }
        response = self.client.put(
            self.url_detail, data=update_data, content_type="application/json"
        )
        assert response.status_code == 200

    def test_retrieve_station_owner(self):
        update_data = {
            "name": "owner2",
            "phone_number": "0100055",
            "email": "owner2@gmail.com",
            "password": "owner1",
            "created_by": self.user.id,
            "updated_by": self.user.id,
            "station": self.station.id,
        }
        response = self.client.get(
            self.url_detail, data=update_data, content_type="application/json"
        )
        assert response.status_code == 200

    def test_delete_station_owner(self):
        response = self.client.delete(self.url_detail)
        assert response.status_code == 204


@pytest.mark.django_db
class TestStationBranchManager:
    @pytest.fixture(autouse=True)
    def sutup(self):
        self.client = Client()
        self.user = User.objects.create(name="user1", phone_number="011020",
                                        email="user1@gmail.com", password="user1", role="admin")
        self.country = Country.objects.create(name="Egypt", code="EG")
        self.city = City.objects.create(name="Cairo", country=self.country)
        self.district = District.objects.create(name="District1", city=self.city)
        self.station = Station.objects.create(name="Station1", address="Address1", lang="3.77",
                                              lat="4.99", district=self.district, created_by=self.user, updated_by=self.user)
        self.station_branch = StationBranch.objects.create(name="Branch1", address="Address1",
                                                           lang="3.77", lat="4.99",
                                                           district=self.district, station=self.station, created_by=self.user, updated_by=self.user)
        self.station_owner = StationOwner.objects.create(name="owner1", phone_number="011020221",
                                                         email="owner1@gmail.com", password="user1", role="admin", station=self.station)
        self.station_branch_manager = StationBranchManager.objects.create(name="manager1", phone_number="01102000",
                                                                          email="manager1@gmail.com", password="user1", role="admin", station_branch=self.station_branch, user=self.station_owner)
        access_token = AccessToken.for_user(self.station_branch_manager)
        self.client.defaults['HTTP_AUTHORIZATION'] = \
            f'Bearer {str(access_token)}'
        self.url_list = reverse("station-branch-managers-list")
        self.url_detail = reverse("station-branch-managers-detail", args=[self.station_branch_manager.id])

    def test_list_station_branch_manager(self):
        response = self.client.get(self.url_list)
        assert response.status_code == 200

    def test_create_station_branch_manager(self):
        data = {'name': "manager2", 'phone_number': "011020004", 'email': "manager2@gmail.com",
                'password': "user1", 'role': "admin", 'station_branch': self.station_branch.id, 'user': self.station_owner.id}
        response = self.client.post(
            self.url_list,
            data=data,
            content_type='application/json'
        )
        assert response.status_code == 201

    def test_update_station_branch_manager(self):
        update_data = {'name': "manager22", 'phone_number': "0110200044", 'email': "manager2@gmail.com",
                       'password': "manager22", 'role': "admin", 'station_branch': self.station_branch.id, 'user': self.station_owner.id}
        response = self.client.put(self.url_detail,
                                   data=update_data,
                                   content_type='application/json'
                                   )
        assert response.status_code == 200

    def test_retrieve_station_branch_manager(self):
        update_data = {'name': "manager22", 'phone_number': "0110200044", 'email': "manager2@gmail.com",
                       'password': "manager22", 'role': "admin", 'station_branch': self.station_branch.id, 'user': self.station_owner.id}

        response = self.client.get(self.url_detail, data=update_data,
                                   content_type='application/json'
                                   )
        assert response.status_code == 200

    def test_delete_station_branch_manager(self):
        response = self.client.delete(self.url_detail)
        assert response.status_code == 204
