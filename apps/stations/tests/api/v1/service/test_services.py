from decimal import Decimal

import pytest
from rest_framework import status

from apps.stations.models.service_models import Service
from apps.stations.tests.helpers import returned_ids, services_detail_url, services_list_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_list_without_authentication_fail(api_client):
    response = api_client.get(services_list_url())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_as_admin_success(
    auth_client, admin_user, service, other_service, diesel_service
):
    response = auth_client(admin_user).get(services_list_url(no_paginate="true"))

    assert response.status_code == status.HTTP_200_OK
    assert {service.id, other_service.id, diesel_service.id}.issubset(
        returned_ids(response)
    )


def test_list_as_station_owner_excludes_assigned_success(
    auth_client,
    station_owner,
    station,
    service,
    other_service,
    diesel_service,
    branch_petrol_service,
):
    response = auth_client(station_owner, station_id=station.id).get(
        services_list_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert service.id not in ids
    assert other_service.id in ids
    assert diesel_service.id in ids


def test_list_as_branch_manager_excludes_assigned_success(
    auth_client,
    branch_manager,
    station,
    service,
    other_service,
    branch_petrol_service,
):
    response = auth_client(branch_manager, station_id=station.id).get(
        services_list_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert service.id not in ids
    assert other_service.id in ids


def test_list_filter_by_type_success(
    auth_client, admin_user, service, other_service, diesel_service
):
    response = auth_client(admin_user).get(
        services_list_url(type="petrol", no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert service.id in ids
    assert other_service.id not in ids
    assert diesel_service.id not in ids


def test_retrieve_success(auth_client, admin_user, service):
    response = auth_client(admin_user).get(services_detail_url(service.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == service.id
    assert response.data["name"] == service.name
    assert response.data["type"] == Service.ServiceType.PETROL
    assert Decimal(response.data["cost"]) == Decimal("10.00")


def test_update_as_admin_success(auth_client, admin_user, service):
    response = auth_client(admin_user).patch(
        services_detail_url(service.id),
        {"name": "Gasoline 95", "cost": "11.50"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    service.refresh_from_db()
    assert service.name == "Gasoline 95"
    assert service.cost == Decimal("11.50")


def test_delete_unused_service_success(auth_client, admin_user, diesel_service):
    response = auth_client(admin_user).delete(services_detail_url(diesel_service.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Service.objects.filter(id=diesel_service.id).exists()


def test_retrieve_without_authentication_fail(api_client, service):
    response = api_client.get(services_detail_url(service.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_as_worker_includes_assigned_success(
    auth_client, station_worker, station, service, branch_petrol_service
):
    response = auth_client(station_worker, station_id=station.id).get(
        services_list_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    assert service.id in returned_ids(response)


def test_list_filter_by_station_success(
    auth_client, admin_user, station, service, other_service, branch_petrol_service
):
    response = auth_client(admin_user).get(
        services_list_url(station=station.id, no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert service.id in ids
    assert other_service.id not in ids


def test_list_filter_by_station_branch_success(
    auth_client, admin_user, branch, service, other_service, branch_petrol_service
):
    response = auth_client(admin_user).get(
        services_list_url(station_branch=branch.id, no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert service.id in ids
    assert other_service.id not in ids


def test_owner_retrieve_assigned_service_fail(
    auth_client, station_owner, station, service, branch_petrol_service
):
    response = auth_client(station_owner, station_id=station.id).get(
        services_detail_url(service.id)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
