import pytest
from django.urls import reverse
from apps.companies.models.operation_model import CarOperation
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from io import BytesIO
from PIL import Image

def create_test_image():
    file = BytesIO()
    image = Image.new('RGB', size=(1, 1), color=(255, 0, 0))
    image.save(file, 'jpeg')
    file.seek(0)
    return SimpleUploadedFile("test_image.jpg", file.read(), content_type="image/jpeg")

@pytest.mark.django_db
class TestStationGasOperations:
    def test_gas_operation_patch_start_time(self, auth_client, station_worker, station, gas_operation):
        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-gas-operations", kwargs={"pk": gas_operation.id})
        response = client.patch(url, {"start_time": timezone.now().isoformat()})
        
        assert response.status_code == 200
        gas_operation.refresh_from_db()
        assert gas_operation.start_time is not None

    def test_gas_operation_patch_car_meter(self, auth_client, station_worker, station, gas_operation):
        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-gas-operations", kwargs={"pk": gas_operation.id})
        
        # Car's last_meter is 10000. Meter must be greater.
        response = client.patch(url, {"car_meter": 10001, "motor_image": create_test_image()}, format="multipart")
        if response.status_code != 200:
            print("ERROR IN CAR METER:", response.data)
        assert response.status_code == 200
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.IN_PROGRESS
        
    def test_gas_operation_patch_invalid_car_meter(self, auth_client, station_worker, station, gas_operation):
        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-gas-operations", kwargs={"pk": gas_operation.id})
        
        # Car's last_meter is 10000. 9999 is invalid.
        response = client.patch(url, {"car_meter": 9999, "motor_image": create_test_image()}, format="multipart")
        if response.status_code == 400:
            print("ERROR IN INVALID CAR METER:", response.data)
        assert response.status_code == 400
        assert "العداد الحالي يجب ان يكون اكبر" in str(response.data)

    def test_gas_operation_patch_amount_success(self, auth_client, station_worker, station, gas_operation):
        # Setup: Set start_time and status to IN_PROGRESS so we can finalize with amount
        gas_operation.start_time = timezone.now()
        gas_operation.status = CarOperation.OperationStatus.IN_PROGRESS
        gas_operation.car_meter = 10050
        gas_operation.save()

        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-gas-operations", kwargs={"pk": gas_operation.id})
        
        # Amount 20 liters. Car has 1000 balance and capacity is 50. This should pass.
        response = client.patch(url, {"amount": 20, "fuel_image": create_test_image()}, format="multipart")
        if response.status_code != 200:
            print("ERROR IN AMOUNT:", response.data)
        assert response.status_code == 200
        
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.COMPLETED
        assert gas_operation.cost > 0
        assert gas_operation.car.balance < 1000.00 # Balance deducted

    def test_gas_operation_patch_not_found(self, auth_client, station_worker, station):
        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-gas-operations", kwargs={"pk": 9999})
        response = client.patch(url, {"amount": 10})
        assert response.status_code == 400
        
    def test_gas_operation_delete(self, auth_client, station_worker, station, gas_operation):
        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-gas-operations", kwargs={"pk": gas_operation.id})
        response = client.delete(url)
        assert response.status_code == 204
        assert not CarOperation.objects.filter(id=gas_operation.id).exists()


@pytest.mark.django_db
class TestStationOtherOperations:
    def test_other_operation_patch_success(self, auth_client, station_worker, station, other_operation, other_service):
        from apps.stations.models.stations_models import StationBranchService
        StationBranchService.objects.create(service=other_service, station_branch=station_worker.station_branch, created_by=station_worker)
        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-other-operations", kwargs={"pk": other_operation.id})
        
        response = client.patch(url, {"service": other_service.id, "cost": 50, "car_image": create_test_image()}, format="multipart")
        assert response.status_code == 200
        
        other_operation.refresh_from_db()
        assert other_operation.status == CarOperation.OperationStatus.COMPLETED
        assert other_operation.car.balance < 1000.00

    def test_other_operation_patch_not_found(self, auth_client, station_worker, station):
        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-other-operations", kwargs={"pk": 9999})
        response = client.patch(url, {"cost": 50})
        assert response.status_code == 400
        
    def test_other_operation_delete(self, auth_client, station_worker, station, other_operation):
        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-other-operations", kwargs={"pk": other_operation.id})
        response = client.delete(url)
        assert response.status_code == 204
        assert not CarOperation.objects.filter(id=other_operation.id).exists()
