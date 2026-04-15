import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch
from rest_framework import status
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.companies.models.operation_model import CarOperation
from apps.companies.models.company_models import Car, Driver, Company, CompanyBranch
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import User, Worker

@pytest.mark.django_db
class TestStationGasOperationAPIView:
    @pytest.fixture
    def setup_data(self, admin_user, geo_data):
        # Create company
        self.company = Company.objects.create(
            name="Test Company",
            balance=Decimal("10000.00"),
            district=geo_data["district"],
            created_by=admin_user
        )
        self.company_branch = CompanyBranch.objects.create(
            name="Test Branch",
            company=self.company,
            district=geo_data["district"],
            fees=Decimal("10.00"), # 10% fees
            created_by=admin_user
        )
        
        # Create station
        self.station = Station.objects.create(
            name="Test Station",
            address="Station Address",
            lang=31.23,
            lat=30.04,
            district=geo_data["district"],
            created_by=admin_user
        )
        self.station_branch = StationBranch.objects.create(
            name="Test Station Branch",
            address="Branch Address",
            lang=31.23,
            lat=30.04,
            station=self.station,
            district=geo_data["district"],
            fees=Decimal("2.00"),
            created_by=admin_user
        )

        # Create worker
        self.worker = Worker.objects.create(
            name="Test Worker",
            phone_number="01012345678",
            email="worker@test.com",
            password="password123",
            role=User.UserRoles.StationWorker,
            station_branch=self.station_branch,
            created_by=admin_user
        )

        # Create service
        self.service = Service.objects.create(
            name="Octane 95",
            cost=Decimal("15.00"),
            type=Service.ServiceType.PETROL,
            unit=Service.ServiceUnit.LITRE,
            created_by=admin_user
        )

        # Create car
        self.car = Car.objects.create(
            code="CAR123",
            plate_number="123",
            plate_character="ABC",
            model_year=2020,
            brand="Toyota",
            is_with_odometer=True,
            tank_capacity=100,
            permitted_fuel_amount=50,
            last_meter=1000,
            balance=Decimal("1000.00"),
            branch=self.company_branch,
            created_by=admin_user,
            number_of_fuelings_per_day=5,
            number_of_washes_per_month=4,
            fuel_allowed_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        )

        # Create driver
        self.driver = Driver.objects.create(
            name="Test Driver",
            phone_number="01087654321",
            lincense_number="DL123",
            lincense_expiration_date=timezone.now().date() + timedelta(days=365),
            branch=self.company_branch,
            created_by=admin_user
        )

        # Create operation
        self.operation = CarOperation.objects.create(
            car=self.car,
            driver=self.driver,
            station_branch=self.station_branch,
            worker=self.worker,
            service=self.service,
            status=CarOperation.OperationStatus.PENDING,
            created_by=admin_user
        )
        
        # Create a mock image
        self.mock_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b',
            content_type='image/jpeg'
        )
        
        return self.worker

    def test_patch_gas_operation_start_meter_success(self, setup_data, auth_client):
        worker = setup_data
        client = auth_client(worker, station_id=self.station.id)
        url = reverse("station-gas-operations", kwargs={"pk": self.operation.pk})
        
        data = {
            "car_meter": 1100,
            "motor_image": self.mock_image
        }
        response = client.patch(url, data, format="multipart")
        
        if response.status_code != status.HTTP_200_OK:
             print(f"DEBUG Response: {response.data}")
        assert response.status_code == status.HTTP_200_OK
        self.operation.refresh_from_db()
        assert self.operation.status == CarOperation.OperationStatus.IN_PROGRESS
        assert self.operation.car_meter == 1100

    def test_patch_gas_operation_invalid_meter_fails(self, setup_data, auth_client):
        worker = setup_data
        client = auth_client(worker, station_id=self.station.id)
        url = reverse("station-gas-operations", kwargs={"pk": self.operation.pk})
        
        data = {
            "car_meter": 900,
            "motor_image": self.mock_image
        }
        response = client.patch(url, data, format="multipart")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "العداد الحالي يجب ان يكون اكبر" in response.data["message"]

    @patch("apps.stations.api.v1.views.car_operations_views.generate_station_transaction")
    @patch("apps.stations.api.v1.views.car_operations_views.generate_company_transaction")
    def test_patch_gas_operation_complete_success(self, mock_comp_tx, mock_station_tx, setup_data, auth_client):
        worker = setup_data
        client = auth_client(worker, station_id=self.station.id)
        url = reverse("station-gas-operations", kwargs={"pk": self.operation.pk})
        
        # 1. Set start meter and start time
        self.operation.status = CarOperation.OperationStatus.IN_PROGRESS
        self.operation.car_meter = 1100
        self.operation.start_time = timezone.localtime()
        self.operation.save()
        
        # 2. Complete operation
        data = {
            "amount": 10,
            "fuel_image": self.mock_image
        }
        
        # Mock time to be within 60 seconds
        now = self.operation.start_time + timedelta(seconds=30)
        with patch("django.utils.timezone.localtime", return_value=now):
            response = client.patch(url, data, format="multipart")
        
        if response.status_code != status.HTTP_200_OK:
             print(f"DEBUG Response: {response.data}")
        assert response.status_code == status.HTTP_200_OK
        self.operation.refresh_from_db()
        assert self.operation.status == CarOperation.OperationStatus.COMPLETED
        assert self.operation.amount == Decimal("10")
        
        # Check car balance update
        self.car.refresh_from_db()
        assert self.car.balance == Decimal("835.00") # 1000 - 165
        
        # Verify transactions
        mock_station_tx.assert_called_once()
        mock_comp_tx.assert_called_once()

    def test_patch_gas_operation_timeout_fails(self, setup_data, auth_client):
        worker = setup_data
        client = auth_client(worker, station_id=self.station.id)
        url = reverse("station-gas-operations", kwargs={"pk": self.operation.pk})
        
        self.operation.status = CarOperation.OperationStatus.IN_PROGRESS
        self.operation.start_time = timezone.localtime()
        self.operation.save()
        
        data = {
            "amount": 10,
            "fuel_image": self.mock_image
        }
        
        # Mock time to be > 60 seconds
        now = self.operation.start_time + timedelta(seconds=61)
        with patch("django.utils.timezone.localtime", return_value=now):
            response = client.patch(url, data, format="multipart")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "الوقت الانتهاء يجب ان يكون اقل من 60 ثانية" in response.data["message"]

    def test_patch_gas_operation_insufficient_balance_fails(self, setup_data, auth_client):
        worker = setup_data
        client = auth_client(worker, station_id=self.station.id)
        url = reverse("station-gas-operations", kwargs={"pk": self.operation.pk})
        
        self.operation.status = CarOperation.OperationStatus.IN_PROGRESS
        self.operation.start_time = timezone.localtime()
        self.operation.save()
        
        # Car balance is 1000, company_liter_cost is 16.5. Max liters approx 60.
        data = {
            "amount": 70,
            "fuel_image": self.mock_image
        }
        
        response = client.patch(url, data, format="multipart")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "الكمية المطلوبة اكبر من الحد الأقصى" in response.data["message"]

    def test_delete_gas_operation_success(self, setup_data, auth_client):
        worker = setup_data
        client = auth_client(worker, station_id=self.station.id)
        url = reverse("station-gas-operations", kwargs={"pk": self.operation.pk})
        
        response = client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CarOperation.objects.filter(id=self.operation.id).exists()
