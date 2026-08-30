import pytest

from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import Station, StationBranch


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

    @pytest.mark.parametrize("fixture_name", ["station", "branch"])
    def test_station_models_are_available_by_default(self, request, fixture_name):
        instance = request.getfixturevalue(fixture_name)

        assert instance.is_available is True

    @pytest.mark.parametrize("fixture_name", ["station", "branch"])
    def test_station_models_can_be_made_unavailable(self, request, fixture_name):
        instance = request.getfixturevalue(fixture_name)

        instance.is_available = False
        instance.save(update_fields=["is_available"])
        instance.refresh_from_db()

        assert instance.is_available is False


@pytest.mark.django_db
class TestServiceModels:
    def test_service_creation(self, admin_user):
        service = Service.objects.create(
            name="Super Petrol",
            unit=Service.ServiceUnit.LITRE,
            type=Service.ServiceType.PETROL,
            cost=12.50,
            created_by=admin_user,
        )
        assert Service.objects.count() == 1
        assert service.name == "Super Petrol"
        assert service.cost == 12.50
        assert str(service) == "Super Petrol"


@pytest.mark.django_db
class TestStationBranchServiceModels:
    def test_branch_service_link(self, branch_petrol_service, branch, service):
        from apps.stations.models.stations_models import StationBranchService

        assert StationBranchService.objects.count() == 1
        assert str(branch_petrol_service) == f"{service.name} - {branch.name}"
