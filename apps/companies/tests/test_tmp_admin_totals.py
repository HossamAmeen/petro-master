from decimal import Decimal

import pytest
from django.urls import reverse

from apps.companies.factories import (
    AdminUserFactory,
    CarFactory,
    CarOperationFactory,
    CompanyBranchFactory,
    CompanyFactory,
    DriverFactory,
    ServiceFactory,
    StationBranchFactory,
    StationFactory,
    WorkerFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def graph(geo_data):
    admin_user = AdminUserFactory()
    company = CompanyFactory(balance=Decimal("100.00"))
    branch = CompanyBranchFactory(company=company, balance=Decimal("50.00"))
    car = CarFactory(branch=branch, balance=Decimal("25.00"))
    driver = DriverFactory(branch=branch)
    station = StationFactory(balance=Decimal("200.00"))
    station_branch = StationBranchFactory(station=station, balance=Decimal("30.00"))
    worker = WorkerFactory(station_branch=station_branch)
    service = ServiceFactory()
    operation = CarOperationFactory(
        car=car,
        driver=driver,
        station_branch=station_branch,
        worker=worker,
        service=service,
    )
    return {
        "admin_user": admin_user,
        "company": company,
        "station": station,
        "operation": operation,
    }


class TestAdminTotals:
    def test_company_changelist_totals_success(self, client, graph):
        client.force_login(graph["admin_user"])
        response = client.get(reverse("admin:companies_company_changelist"))

        assert response.status_code == 200
        assert response.context_data["sum_total_balance"] == Decimal("175.00")
        assert response.context_data["sum_operations_count"] == 1
        row = response.context_data["cl"].result_list.get()
        assert row.total_balance_sum == Decimal("175.00")
        assert row.operations_count == 1

    def test_station_changelist_totals_success(self, client, graph):
        client.force_login(graph["admin_user"])
        response = client.get(reverse("admin:stations_station_changelist"))

        assert response.status_code == 200
        assert response.context_data["sum_total_balance"] == Decimal("230.00")
        assert response.context_data["sum_operations_count"] == 1
        row = response.context_data["cl"].result_list.get()
        assert row.total_balance_sum == Decimal("230.00")
        assert row.operations_count == 1

    def test_operations_links_success(self, client, graph):
        client.force_login(graph["admin_user"])
        operations_url = reverse("admin:companies_caroperation_changelist")

        company_response = client.get(
            operations_url,
            {"car__branch__company__id__exact": graph["company"].id},
        )
        station_response = client.get(
            operations_url,
            {"station_branch__station__id__exact": graph["station"].id},
        )

        assert company_response.status_code == 200
        assert station_response.status_code == 200
        assert list(company_response.context_data["cl"].result_list) == [
            graph["operation"]
        ]
        assert list(station_response.context_data["cl"].result_list) == [
            graph["operation"]
        ]

    def test_company_totals_respect_filters_success(self, client, graph):
        other_company = CompanyFactory(balance=Decimal("999.00"))
        client.force_login(graph["admin_user"])

        response = client.get(
            reverse("admin:companies_company_changelist"),
            {"q": graph["company"].name},
        )

        assert response.status_code == 200
        assert other_company.id not in [
            row.id for row in response.context_data["cl"].result_list
        ]
        assert response.context_data["sum_total_balance"] == Decimal("175.00")
