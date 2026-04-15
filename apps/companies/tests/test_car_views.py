from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.companies.models.company_models import Car, Company, CompanyBranch
from apps.geo.models import City, Country, District
from apps.shared.base_exception_class import CustomValidationError
from apps.users.models import CompanyUser, User


@pytest.mark.django_db
class TestCarViewSetUpdateBalance:
    def setup_method(self, db):
        # Create test data
        self.country = Country.objects.create(name="Egypt", code="EGP")
        self.city = City.objects.create(name="Cairo", country=self.country)
        self.district = District.objects.create(name="Nasr City", city=self.city)
        admin = User.objects.create(
            role=User.UserRoles.Admin,
            email="admin@test.com",
            name="Admin",
            phone_number="1111111111"
        )
        # Create company and branch
        self.company = Company.objects.create(
            name="Test Company",
            balance=Decimal("1000.00"),
            is_active=True,
            created_by=admin,
            updated_by=admin
        )
        self.branch = CompanyBranch.objects.create(
            name="Test Branch",
            company=self.company,
            district=self.district,
            balance=Decimal("500.00"),
            created_by=admin,
            updated_by=admin
        )
        
        # Create car
        self.car = Car.objects.create(
            code="CAR001",
            plate_number="1234",
            plate_character="ABC",
            balance=Decimal("100.00"),
            branch=self.branch,
            is_blocked_balance_update=False,
            permitted_fuel_amount=Decimal("1000.00"),
            tank_capacity=Decimal("2000.00"),
            model_year=2020,
            is_with_odometer=True,
            number_of_fuelings_per_day=10,
            number_of_washes_per_month=5,
            created_by=admin,
            updated_by=admin
        )
        
        # Create users
        self.company_owner = CompanyUser.objects.create(
            role=User.UserRoles.CompanyOwner,
            email="owner@test.com",
            name="Owner",
            phone_number="1234567890",
            company=self.company,
        )
        
        self.branch_manager = CompanyUser.objects.create(
            role=User.UserRoles.CompanyBranchManager,
            email="manager@test.com",
            name="Manager",
            phone_number="0987654321",
            company=self.company,
        )
        
        # Add manager to branch
        from apps.users.models import CompanyBranchManager
        CompanyBranchManager.objects.create(
            user=self.branch_manager,
            company_branch=self.branch,
            created_by=admin,
            updated_by=admin
        )
        self.url = reverse("cars-update_balance", kwargs={"pk": self.car.pk})
    
    def get_client(self, user):
        """Get authenticated client for user"""
        access_token = AccessToken.for_user(user)
        access_token["company_id"] = self.company.id
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        return client
    
    @patch('apps.companies.api.v1.views.car_views.generate_company_transaction')
    @patch('apps.notifications.models.Notification.objects.create')
    def test_add_balance_as_company_owner_success(self, mock_notification, mock_transaction):
        """Test adding balance to car as company owner"""
        client = self.get_client(self.company_owner)
        
        
        data = {
            "amount": "50.00",
            "type": "add"
        }
        
        response = client.post(self.url, data, format='json')
        
        assert response.status_code == 200
        assert response.data["balance"] == Decimal("150.00")
        
        # Refresh objects from database
        self.car.refresh_from_db()
        self.company.refresh_from_db()
        self.branch.refresh_from_db()
        
        assert self.car.balance == Decimal("150.00")
        assert self.company.balance == Decimal("950.00")  # Company balance decreased
        
        # Verify transaction was created
        mock_transaction.assert_called_once()
        # Verify notification was created
        assert mock_notification.call_count == 2  # Owner + manager
    
    @patch('apps.companies.api.v1.views.car_views.generate_company_transaction')
    @patch('apps.notifications.models.Notification.objects.create')
    def test_add_balance_as_branch_manager_success(self, mock_notification, mock_transaction):
        """Test adding balance to car as branch manager"""
        client = self.get_client(self.branch_manager)
        url = reverse("cars-update_balance", kwargs={"pk": self.car.pk})
        
        data = {
            "amount": "30.00",
            "type": "add"
        }
        
        response = client.post(url, data, format='json')
        
        assert response.status_code == 200
        assert response.data["balance"] == Decimal("130.00")
        
        # Refresh objects from database
        self.car.refresh_from_db()
        self.branch.refresh_from_db()
        
        assert self.car.balance == Decimal("130.00")
        assert self.branch.balance == Decimal("470.00")  # Branch balance decreased
        
        # Verify transaction was created
        mock_transaction.assert_called_once()
        # Verify notification was created
        assert mock_notification.call_count == 2  # Manager + owner
    
    @patch('apps.companies.api.v1.views.car_views.generate_company_transaction')
    @patch('apps.notifications.models.Notification.objects.create')
    def test_subtract_balance_as_company_owner_success(self, mock_notification, mock_transaction):
        """Test subtracting balance from car as company owner"""
        client = self.get_client(self.company_owner)
        url = reverse("cars-update_balance", kwargs={"pk": self.car.pk})
        
        data = {
            "amount": "25.00",
            "type": "subtract"
        }
        
        response = client.post(url, data, format='json')
        
        assert response.status_code == 200
        assert response.data["balance"] == Decimal("75.00")
        
        # Refresh objects from database
        self.car.refresh_from_db()
        self.company.refresh_from_db()
        
        assert self.car.balance == Decimal("75.00")
        assert self.company.balance == Decimal("1025.00")  # Company balance increased
        
        # Verify transaction was created
        mock_transaction.assert_called_once()
        # Verify notification was created
        assert mock_notification.call_count == 2
    
    def test_add_balance_insufficient_fails(self):
        """Test adding balance when company/branch has insufficient funds"""
        client = self.get_client(self.company_owner)
        url = reverse("cars-update_balance", kwargs={"pk": self.car.pk})
        
        # Try to add more than company balance
        data = {
            "amount": "1500.00",  # More than company balance (1000)
            "type": "add"
        }
        
        response = client.post(url, data, format='json')
        
        assert response.status_code == 400
        assert "الرصيد غير كافٍ" in response.data["message"]
    
    def test_subtract_balance_insufficient_fails(self):
        """Test subtracting balance when car has insufficient funds"""
        client = self.get_client(self.company_owner)
        url = reverse("cars-update_balance", kwargs={"pk": self.car.pk})
        
        # Try to subtract more than car balance
        data = {
            "amount": "200.00",  # More than car balance (100)
            "type": "subtract"
        }
        
        response = client.post(url, data, format='json')
        
        assert response.status_code == 400
        assert "السيارة لا تمتلك كافٍ من المال" in response.data["message"]
    
    def test_update_balance_blocked_car_fails(self):
        """Test updating balance when car is blocked"""
        self.car.is_blocked_balance_update = True
        self.car.save()
        
        client = self.get_client(self.company_owner)
        url = reverse("cars-update_balance", kwargs={"pk": self.car.pk})
        
        data = {
            "amount": "50.00",
            "type": "add"
        }
        
        response = client.post(url, data, format='json')
        
        assert response.status_code == 400
        assert "لا يمكن تحديث رصيد السيارة حاليا" in response.data["message"]
    
    def test_update_balance_invalid_serializer_data(self):
        """Test updating balance with invalid serializer data"""
        client = self.get_client(self.company_owner)
        url = reverse("cars-update_balance", kwargs={"pk": self.car.pk})
        
        # Invalid amount (negative)
        data = {
            "amount": "-10.00",
            "type": "add"
        }
        
        response = client.post(url, data, format='json')
        
        assert response.status_code == 400
    
    def test_update_balance_invalid_type(self):
        """Test updating balance with invalid type"""
        client = self.get_client(self.company_owner)
        url = reverse("cars-update_balance", kwargs={"pk": self.car.pk})
        
        # Invalid type
        data = {
            "amount": "50.00",
            "type": "invalid"
        }
        
        response = client.post(url, data, format='json')
        
        assert response.status_code == 400
