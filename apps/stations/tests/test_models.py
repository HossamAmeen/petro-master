import pytest
from apps.stations.models.stations_models import Station, StationBranch
from apps.stations.models.service_models import Service

@pytest.mark.django_db
class TestStationModels:
    def test_station_creation(self, station):
        assert Station.objects.count() == 1
        assert station.name == "Station 1"
        assert station.balance == 0
        assert str(station) == "Station 1"

    def test_branch_creation(self, branch):
        assert StationBranch.objects.count() == 1
        assert branch.name == "Branch 1"
        assert branch.station.name == "Station 1"
        assert branch.fees == 0.0
        assert str(branch) == f"{branch.name} - {branch.station.name}"

@pytest.mark.django_db
class TestServiceModels:
    def test_service_creation(self, admin_user):
        service = Service.objects.create(
            name="Super Petrol",
            unit=Service.ServiceUnit.LITRE,
            type=Service.ServiceType.PETROL,
            cost=12.50,
            created_by=admin_user
        )
        assert Service.objects.count() == 1
        assert service.name == "Super Petrol"
        assert service.cost == 12.50
        assert str(service) == "Super Petrol"
