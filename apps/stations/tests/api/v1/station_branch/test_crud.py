from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounting.models import StationKhaznaTransaction
from apps.notifications.models import Notification
from apps.stations.models.stations_models import StationBranch, StationBranchService
from apps.stations.tests.helpers import (
    branches_detail_url,
    branches_list_url,
    notification_user_ids,
    returned_ids,
    set_balance,
)
from apps.users.models import StationBranchManager

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def update_balance_url(pk):
    return reverse("station-branches-update-balance", kwargs={"pk": pk})


def assign_managers_url(pk):
    return reverse("station-branches-assign-managers", kwargs={"pk": pk})


def assign_services_url(pk):
    return reverse("station-branches-assign-services", kwargs={"pk": pk})


def add_service_url(pk):
    return reverse("station-branches-add-service", kwargs={"pk": pk})


def delete_service_url(pk):
    return reverse("station-branches-delete-service", kwargs={"pk": pk})


def services_url(pk, **params):
    url = reverse("station-branches-services", kwargs={"pk": pk})
    if params:
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{url}?{query}"
    return url


def available_services_url(pk, **params):
    url = reverse("station-branches-available-services", kwargs={"pk": pk})
    if params:
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{url}?{query}"
    return url


class TestStationBranchCRUD:
    def test_list_public_success(self, api_client, branch, other_station_branch):
        response = api_client.get(branches_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        assert {branch.id, other_station_branch.id}.issubset(returned_ids(response))
        row = next(item for item in response.data["results"] if item["id"] == branch.id)
        assert set(row) >= {"id", "name", "address", "district", "station"}
        assert "managers_count" not in row

    def test_list_as_station_owner_scoped_success(
        self, auth_client, station_owner, station, branch, other_station_branch
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            branches_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert branch.id in ids
        assert other_station_branch.id not in ids
        row = next(item for item in response.data["results"] if item["id"] == branch.id)
        assert "services" in row
        assert "managers_count" in row

    def test_list_as_branch_manager_scoped_success(
        self, auth_client, branch_manager, station, branch, second_station_branch
    ):
        response = auth_client(branch_manager, station_id=station.id).get(
            branches_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert branch.id in ids
        assert second_station_branch.id not in ids

    def test_list_as_dashboard_includes_counts_success(
        self,
        auth_client,
        admin_user,
        branch,
        station_worker,
        branch_manager,
        branch_petrol_service,
    ):
        response = auth_client(admin_user).get(branches_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        row = next(item for item in response.data["results"] if item["id"] == branch.id)
        assert row["workers_count"] >= 1
        assert row["managers_count"] >= 1
        assert row["services_count"] >= 1

    def test_list_filter_by_station_success(
        self, api_client, branch, other_station_branch, station
    ):
        response = api_client.get(
            branches_list_url(station=station.id, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert branch.id in ids
        assert other_station_branch.id not in ids

    def test_create_without_authentication_fail(
        self, api_client, station_branch_payload_factory
    ):
        response = api_client.post(
            reverse("station-branches-list"),
            station_branch_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role_fixture",
        ["station_owner", "station_worker", "company_owner"],
    )
    def test_create_forbidden_role_fail(
        self,
        role_fixture,
        request,
        auth_client,
        company,
        station,
        station_branch_payload_factory,
    ):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture == "company_owner":
            client_kwargs["company_id"] = company.id
        if role_fixture in {"station_owner", "station_worker"}:
            client_kwargs["station_id"] = station.id
        existing = set(StationBranch.objects.values_list("id", flat=True))

        response = auth_client(user, **client_kwargs).post(
            reverse("station-branches-list"),
            station_branch_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert set(StationBranch.objects.values_list("id", flat=True)) == existing

    def test_create_as_admin_success(
        self, auth_client, admin_user, station, geo_data, station_branch_payload_factory
    ):
        payload = station_branch_payload_factory(fees="1.50")

        response = auth_client(admin_user).post(
            reverse("station-branches-list"), payload, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = StationBranch.objects.get(name=payload["name"])
        assert created.station_id == station.id
        assert created.fees == Decimal("1.50")
        assert created.created_by_id == admin_user.id

    def test_retrieve_as_station_owner_success(
        self, auth_client, station_owner, station, branch
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            branches_detail_url(branch.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == branch.id
        assert response.data["name"] == branch.name

    def test_update_as_admin_success(self, auth_client, admin_user, branch):
        response = auth_client(admin_user).patch(
            branches_detail_url(branch.id),
            {"name": "Renamed Branch", "fees": "3.25"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        branch.refresh_from_db()
        assert branch.name == "Renamed Branch"
        assert branch.fees == Decimal("3.25")

    def test_delete_empty_branch_as_admin_success(
        self, auth_client, admin_user, station_branch_factory
    ):
        empty = station_branch_factory(name="Deletable Branch")

        response = auth_client(admin_user).delete(branches_detail_url(empty.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not StationBranch.objects.filter(id=empty.id).exists()

    def test_update_balance_without_authentication_fail(self, api_client, branch):
        response = api_client.post(
            update_balance_url(branch.id),
            {"type": "add", "amount": "10.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role_fixture",
        ["admin_user", "branch_manager", "station_worker", "company_owner"],
    )
    def test_update_balance_forbidden_role_fail(
        self, role_fixture, request, auth_client, company, station, branch
    ):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture == "company_owner":
            client_kwargs["company_id"] = company.id
        if role_fixture in {"branch_manager", "station_worker"}:
            client_kwargs["station_id"] = station.id

        response = auth_client(user, **client_kwargs).post(
            update_balance_url(branch.id),
            {"type": "add", "amount": "10.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_add_balance_as_station_owner_success(
        self, auth_client, station_owner, station, branch, branch_manager
    ):
        set_balance(station, "100.00")
        set_balance(branch, "20.00")

        response = auth_client(station_owner, station_id=station.id).post(
            update_balance_url(branch.id),
            {"type": "add", "amount": "40.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["balance"] == Decimal("60.00")
        station.refresh_from_db()
        branch.refresh_from_db()
        assert station.balance == Decimal("60.00")
        assert branch.balance == Decimal("60.00")

        txn = StationKhaznaTransaction.objects.get()
        assert txn.station_id == station.id
        assert txn.station_branch_id == branch.id
        assert txn.amount == Decimal("40.00")
        assert txn.is_internal is True
        assert txn.status == StationKhaznaTransaction.TransactionStatus.APPROVED

        users = notification_user_ids(Notification.NotificationType.MONEY)
        assert users == {station_owner.id, branch_manager.id}

    def test_add_balance_insufficient_station_fail(
        self, auth_client, station_owner, station, branch
    ):
        set_balance(station, "5.00")

        response = auth_client(station_owner, station_id=station.id).post(
            update_balance_url(branch.id),
            {"type": "add", "amount": "10.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_enough_balance"
        station.refresh_from_db()
        branch.refresh_from_db()
        assert station.balance == Decimal("5.00")
        assert branch.balance == Decimal("0.00")
        assert StationKhaznaTransaction.objects.count() == 0
        assert Notification.objects.count() == 0

    def test_subtract_balance_as_station_owner_success(
        self, auth_client, station_owner, station, branch, branch_manager
    ):
        set_balance(station, "10.00")
        set_balance(branch, "50.00")

        response = auth_client(station_owner, station_id=station.id).post(
            update_balance_url(branch.id),
            {"type": "subtract", "amount": "20.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        station.refresh_from_db()
        branch.refresh_from_db()
        assert station.balance == Decimal("30.00")
        assert branch.balance == Decimal("30.00")

        txn = StationKhaznaTransaction.objects.get()
        assert txn.station_branch_id is None
        assert txn.amount == Decimal("20.00")
        assert txn.is_internal is True
        assert notification_user_ids(Notification.NotificationType.MONEY) == {
            station_owner.id,
            branch_manager.id,
        }

    def test_subtract_balance_insufficient_branch_fail(
        self, auth_client, station_owner, station, branch
    ):
        set_balance(branch, "5.00")

        response = auth_client(station_owner, station_id=station.id).post(
            update_balance_url(branch.id),
            {"type": "subtract", "amount": "10.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_enough_balance"
        branch.refresh_from_db()
        assert branch.balance == Decimal("5.00")

    def test_update_balance_amount_below_minimum_fail(
        self, auth_client, station_owner, station, branch
    ):
        set_balance(station, "100.00")

        response = auth_client(station_owner, station_id=station.id).post(
            update_balance_url(branch.id),
            {"type": "add", "amount": "9.99"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_managers_success(
        self,
        auth_client,
        station_owner,
        station,
        branch,
        branch_manager,
        second_station_owner,
    ):
        response = auth_client(station_owner, station_id=station.id).post(
            assign_managers_url(branch.id),
            {"managers": [second_station_owner.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assigned = set(
            StationBranchManager.objects.filter(station_branch=branch).values_list(
                "user_id", flat=True
            )
        )
        assert assigned == {second_station_owner.id}
        assert branch_manager.id not in assigned

    def test_assign_managers_invalid_station_fail(
        self, auth_client, station_owner, station, branch, other_station_owner
    ):
        response = auth_client(station_owner, station_id=station.id).post(
            assign_managers_url(branch.id),
            {"managers": [other_station_owner.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            StationBranchManager.objects.filter(
                station_branch=branch, user=other_station_owner
            ).count()
            == 0
        )

    def test_assign_services_replaces_existing_success(
        self,
        auth_client,
        admin_user,
        branch,
        service,
        other_service,
        diesel_service,
        branch_petrol_service,
    ):
        response = auth_client(admin_user).post(
            assign_services_url(branch.id),
            {"services": [other_service.id, diesel_service.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        linked = set(
            StationBranchService.objects.filter(station_branch=branch).values_list(
                "service_id", flat=True
            )
        )
        assert linked == {other_service.id, diesel_service.id}
        assert service.id not in linked

    def test_add_service_success(
        self,
        auth_client,
        admin_user,
        branch,
        other_service,
        branch_petrol_service,
        service,
    ):
        response = auth_client(admin_user).post(
            add_service_url(branch.id),
            {"services": [other_service.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        linked = set(
            StationBranchService.objects.filter(station_branch=branch).values_list(
                "service_id", flat=True
            )
        )
        assert linked == {service.id, other_service.id}

    def test_add_service_already_exists_fail(
        self, auth_client, admin_user, branch, service, branch_petrol_service
    ):
        response = auth_client(admin_user).post(
            add_service_url(branch.id),
            {"services": [service.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "service_exists"

    def test_delete_service_success(
        self,
        auth_client,
        admin_user,
        branch,
        service,
        other_service,
        branch_petrol_service,
    ):
        StationBranchService.objects.create(
            station_branch=branch,
            service=other_service,
            created_by=admin_user,
        )

        response = auth_client(admin_user).post(
            delete_service_url(branch.id),
            {"services": [service.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        linked = set(
            StationBranchService.objects.filter(station_branch=branch).values_list(
                "service_id", flat=True
            )
        )
        assert linked == {other_service.id}

    def test_list_branch_services_success(
        self,
        auth_client,
        station_owner,
        station,
        branch,
        service,
        other_service,
        branch_petrol_service,
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            services_url(branch.id, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert service.id in ids
        assert other_service.id not in ids

    def test_list_available_services_excludes_assigned_success(
        self,
        auth_client,
        station_owner,
        station,
        branch,
        service,
        other_service,
        branch_petrol_service,
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            available_services_url(branch.id, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert other_service.id in ids
        assert service.id not in ids

    def test_list_branch_services_filter_category_success(
        self,
        auth_client,
        station_owner,
        station,
        branch,
        service,
        other_service,
        branch_petrol_service,
        branch_other_service,
    ):
        petrol = auth_client(station_owner, station_id=station.id).get(
            services_url(branch.id, service_category="petrol", no_paginate="true")
        )
        other = auth_client(station_owner, station_id=station.id).get(
            services_url(branch.id, service_category="other", no_paginate="true")
        )

        assert petrol.status_code == status.HTTP_200_OK
        assert other.status_code == status.HTTP_200_OK
        assert returned_ids(petrol) == {service.id}
        assert returned_ids(other) == {other_service.id}

    def test_list_filter_by_city_success(
        self, api_client, branch, other_station_branch, geo_data, station_branch_factory
    ):
        from apps.geo.models import City, District

        city = City.objects.create(name="Giza City", country=geo_data["country"])
        district = District.objects.create(name="Dokki Filter", city=city)
        giza_branch = station_branch_factory(name="Giza Branch", district=district)

        response = api_client.get(
            branches_list_url(city=geo_data["city"].id, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert branch.id in ids
        assert giza_branch.id not in ids

    def test_list_filter_by_landing_page_success(
        self, api_client, branch, station_branch_factory
    ):
        landing = station_branch_factory(
            name="Landing Branch", is_for_landing_page=True
        )

        response = api_client.get(
            branches_list_url(is_for_landing_page="true", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert landing.id in ids
        assert branch.id not in ids

    def test_list_as_worker_unscoped_success(
        self, auth_client, station_worker, station, branch, other_station_branch
    ):
        response = auth_client(station_worker, station_id=station.id).get(
            branches_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert branch.id in ids
        assert other_station_branch.id in ids

    def test_retrieve_without_authentication_fail(self, api_client, branch):
        response = api_client.get(branches_detail_url(branch.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_other_station_as_owner_fail(
        self, auth_client, station_owner, station, other_station_branch
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            branches_detail_url(other_station_branch.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_as_station_owner_success(
        self, auth_client, station_owner, station, branch
    ):
        response = auth_client(station_owner, station_id=station.id).patch(
            branches_detail_url(branch.id),
            {"name": "Owner Renamed Branch"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        branch.refresh_from_db()
        assert branch.name == "Owner Renamed Branch"

    def test_update_balance_invalid_type_fail(
        self, auth_client, station_owner, station, branch
    ):
        response = auth_client(station_owner, station_id=station.id).post(
            update_balance_url(branch.id),
            {"type": "transfer", "amount": "10.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_balance_other_station_branch_fail(
        self, auth_client, station_owner, station, other_station_branch
    ):
        response = auth_client(station_owner, station_id=station.id).post(
            update_balance_url(other_station_branch.id),
            {"type": "add", "amount": "10.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_managers_without_authentication_fail(
        self, api_client, branch, branch_manager
    ):
        response = api_client.post(
            assign_managers_url(branch.id),
            {"managers": [branch_manager.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_assign_services_empty_clears_existing_success(
        self, auth_client, admin_user, branch, branch_petrol_service, service
    ):
        assert StationBranchService.objects.filter(station_branch=branch).exists()

        response = auth_client(admin_user).post(
            assign_services_url(branch.id),
            {"services": []},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert not StationBranchService.objects.filter(station_branch=branch).exists()

    def test_delete_service_empty_list_success(
        self, auth_client, admin_user, branch, service, branch_petrol_service
    ):
        response = auth_client(admin_user).post(
            delete_service_url(branch.id),
            {"services": []},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert StationBranchService.objects.filter(
            station_branch=branch, service=service
        ).exists()

    def test_add_multiple_services_success(
        self,
        auth_client,
        admin_user,
        branch,
        other_service,
        diesel_service,
        branch_petrol_service,
    ):
        response = auth_client(admin_user).post(
            add_service_url(branch.id),
            {"services": [other_service.id, diesel_service.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        linked = set(
            StationBranchService.objects.filter(station_branch=branch).values_list(
                "service_id", flat=True
            )
        )
        assert {other_service.id, diesel_service.id}.issubset(linked)

    def test_list_branch_services_types_and_search_success(
        self,
        auth_client,
        station_owner,
        station,
        branch,
        service,
        other_service,
        branch_petrol_service,
        branch_other_service,
    ):
        types_resp = auth_client(station_owner, station_id=station.id).get(
            services_url(branch.id, types="petrol", no_paginate="true")
        )
        search_resp = auth_client(station_owner, station_id=station.id).get(
            services_url(branch.id, search=service.name, no_paginate="true")
        )

        assert types_resp.status_code == status.HTTP_200_OK
        assert search_resp.status_code == status.HTTP_200_OK
        assert returned_ids(types_resp) == {service.id}
        assert returned_ids(search_resp) == {service.id}

    def test_list_branch_services_as_manager_excludes_unmanaged_success(
        self,
        auth_client,
        branch_manager,
        station,
        branch,
        second_station_branch,
        service,
        other_service,
        branch_petrol_service,
        station_branch_service_factory,
    ):
        station_branch_service_factory(second_station_branch, other_service)

        own = auth_client(branch_manager, station_id=station.id).get(
            services_url(branch.id, no_paginate="true")
        )
        other = auth_client(branch_manager, station_id=station.id).get(
            services_url(second_station_branch.id, no_paginate="true")
        )

        assert own.status_code == status.HTTP_200_OK
        assert service.id in returned_ids(own)
        assert other.status_code == status.HTTP_200_OK
        assert returned_ids(other) == set()

    def test_available_services_search_and_category_success(
        self,
        auth_client,
        station_owner,
        station,
        branch,
        service,
        other_service,
        diesel_service,
        branch_petrol_service,
    ):
        search = auth_client(station_owner, station_id=station.id).get(
            available_services_url(
                branch.id, search=other_service.name, no_paginate="true"
            )
        )
        category = auth_client(station_owner, station_id=station.id).get(
            available_services_url(
                branch.id, service_category="petrol", no_paginate="true"
            )
        )

        assert search.status_code == status.HTTP_200_OK
        assert category.status_code == status.HTTP_200_OK
        assert other_service.id in returned_ids(search)
        assert service.id not in returned_ids(search)
        assert diesel_service.id in returned_ids(category)
        assert other_service.id not in returned_ids(category)
        assert service.id not in returned_ids(category)
