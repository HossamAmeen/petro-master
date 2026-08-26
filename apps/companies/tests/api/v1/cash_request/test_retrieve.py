from decimal import Decimal

import pytest
from rest_framework import status

from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.tests.api.v1.cash_request.helpers import (
    assert_cash_request_payload,
    cash_request_detail_url,
)


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCashRequestRetrieve:


    def test_retrieve_without_authentication_fail(self,
        api_client, company, company_driver, cash_request_factory
    ):
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = api_client.get(cash_request_detail_url(cash_request.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_retrieve_as_company_owner_success(self,
        auth_client,
        company_owner,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = auth_client(company_owner, company_id=company.id).get(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert_cash_request_payload(response.data, cash_request, company_owner)
        assert response.data["otp"] == cash_request.otp
        assert response.data["code"] == cash_request.code
        assert response.data["driver"]["id"] == company_driver.id
        assert response.data["driver"]["name"] == company_driver.name
        assert response.data["driver"]["phone_number"] == company_driver.phone_number
        assert response.data["driver"]["branch"] == company_driver.branch_id
        assert response.data["driver"]["code"] == company_driver.code
        assert response.data["amount"] == "50.00"
        assert response.data["company_cost"] == "50.00"
        assert response.data["station_cost"] is None
        assert response.data["status"] == CompanyCashRequest.Status.IN_PROGRESS
        assert response.data["company"] == company.id
        assert response.data["is_owner"] is True
        assert response.data["station_branch"] is None
        assert response.data["approved_by"] is None
        assert response.data["worker"] is None


    def test_retrieve_approved_request_as_station_worker_success(self,
        auth_client,
        station_worker,
        station,
        branch,
        geo_data,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            station=station,
            station_branch=branch,
            status=CompanyCashRequest.Status.APPROVED,
            company_cost=Decimal("55.00"),
            station_cost=Decimal("52.50"),
            approved_by=station_worker,
        )

        response = auth_client(station_worker, station_id=station.id).get(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert_cash_request_payload(response.data, cash_request, station_worker)
        assert response.data["amount"] == "52.50"
        assert response.data["company_cost"] == "55.00"
        assert response.data["station_cost"] == "52.50"
        assert response.data["status"] == CompanyCashRequest.Status.APPROVED
        assert response.data["is_owner"] is False
        assert response.data["station_branch"] == {
            "id": branch.id,
            "name": branch.name,
            "address": branch.address,
            "district": {
                "id": geo_data["district"].id,
                "name": geo_data["district"].name,
                "city": {"name": geo_data["city"].name},
            },
            "station": station.id,
        }
        assert response.data["approved_by"] == {
            "id": station_worker.id,
            "name": station_worker.name,
            "phone_number": station_worker.phone_number,
            "role": station_worker.role,
        }
        assert response.data["worker"] == response.data["approved_by"]


    def test_retrieve_as_creator_branch_manager_success(self,
        auth_client,
        company_branch_manager,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            created_by=company_branch_manager,
        )

        response = auth_client(company_branch_manager, company_id=company.id).get(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert_cash_request_payload(response.data, cash_request, company_branch_manager)
        assert response.data["is_owner"] is True


    def test_retrieve_other_user_request_as_branch_manager_fail(self,
        auth_client,
        company_branch_manager,
        company_owner,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            created_by=company_owner,
        )

        response = auth_client(company_branch_manager, company_id=company.id).get(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == "permission_denied"
        assert company_owner.name in str(response.data["message"])


    def test_retrieve_in_progress_as_station_worker_success(self,
        auth_client,
        station_worker,
        station,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = auth_client(station_worker, station_id=station.id).get(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert_cash_request_payload(response.data, cash_request, station_worker)
        assert response.data["amount"] == "None"
        assert response.data["is_owner"] is False
        assert response.data["station_branch"] is None


    def test_retrieve_unlinked_request_as_station_owner_fail(self,
        auth_client,
        station_owner,
        station,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = auth_client(station_owner, station_id=station.id).get(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


    def test_retrieve_other_company_as_owner_fail(self,
        auth_client,
        company_owner,
        company,
        other_company_branch,
        driver_factory,
        cash_request_factory,
    ):
        other = cash_request_factory(
            company=other_company_branch.company,
            driver=driver_factory(branch=other_company_branch),
        )

        response = auth_client(company_owner, company_id=company.id).get(
            cash_request_detail_url(other.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


    def test_retrieve_unknown_request_fail(self, auth_client, company_owner, company):
        response = auth_client(company_owner, company_id=company.id).get(
            cash_request_detail_url(999_999)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
