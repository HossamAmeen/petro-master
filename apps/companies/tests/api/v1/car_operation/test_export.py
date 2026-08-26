import os
from urllib.parse import parse_qs, urlparse

import pytest
from django.conf import settings
from rest_framework import status

from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.api.v1.car_operation.helpers import (
    operation_download_url,
    operation_export_url,
)
from apps.notifications.models import Notification


pytestmark = [pytest.mark.api, pytest.mark.django_db]


@pytest.fixture
def export_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


def test_export_without_authentication_fail(api_client):
    response = api_client.get(operation_export_url())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "role_fixture",
    ["admin_user", "station_worker", "station_owner", "finance_user"],
)
def test_export_forbidden_role_fail(
    role_fixture, request, auth_client, company, station
):
    user = request.getfixturevalue(role_fixture)
    client_kwargs = {}
    if role_fixture in {"station_worker", "station_owner"}:
        client_kwargs["station_id"] = station.id

    response = auth_client(user, **client_kwargs).get(operation_export_url())

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_export_without_completed_operations_fail(
    auth_client, company_owner, company, car_operation_factory
):
    car_operation_factory(status=CarOperation.OperationStatus.PENDING)

    response = auth_client(company_owner, company_id=company.id).get(
        operation_export_url()
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["message"] == "لا توجد بيانات للاستخراج"


def test_export_as_company_owner_success(
    auth_client,
    company_owner,
    company,
    car_operation_factory,
    export_media_root,
):
    operation = car_operation_factory(status=CarOperation.OperationStatus.COMPLETED)

    response = auth_client(company_owner, company_id=company.id).get(
        operation_export_url()
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["message"] == (
        "يتم الان استخراج العمليات وسوف يتم ارسال اليك اشعار لك لتحميل الملف بعد الانتهاء"
    )
    assert response.data["query_param"] == {
        "car": None,
        "date_from": None,
        "date_to": None,
    }
    download_url = response.data["download_url"]
    assert "/api/v1/companies/car-operations/download-excel/?file=" in download_url
    filename = parse_qs(urlparse(download_url).query)["file"][0]
    assert os.path.exists(
        os.path.join(settings.MEDIA_ROOT, "excel_exports", filename)
    )
    notification = Notification.objects.get(
        user_id=company_owner.id, type=Notification.NotificationType.GENERAL
    )
    assert notification.title == "يتم الان استخراج العمليات"
    assert notification.url == download_url
    assert operation.id


def test_export_as_branch_manager_only_managed_branch_success(
    auth_client,
    company_branch_manager,
    company,
    car_factory,
    driver_factory,
    second_company_branch,
    car_operation_factory,
    export_media_root,
):
    managed = car_operation_factory(status=CarOperation.OperationStatus.COMPLETED)
    car_operation_factory(
        status=CarOperation.OperationStatus.COMPLETED,
        car=car_factory(branch=second_company_branch),
        driver=driver_factory(branch=second_company_branch),
    )

    response = auth_client(company_branch_manager, company_id=company.id).get(
        operation_export_url()
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    assert managed.id
    assert os.listdir(os.path.join(settings.MEDIA_ROOT, "excel_exports"))


def test_export_filter_by_car_success(
    auth_client,
    company_owner,
    company,
    car_factory,
    driver_factory,
    car_operation_factory,
    export_media_root,
):
    matching = car_operation_factory(status=CarOperation.OperationStatus.COMPLETED)
    car_operation_factory(
        status=CarOperation.OperationStatus.COMPLETED,
        car=car_factory(),
        driver=driver_factory(),
    )

    response = auth_client(company_owner, company_id=company.id).get(
        operation_export_url(),
        {"car": matching.car_id},
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["query_param"]["car"] == str(matching.car_id)


def test_export_invalid_date_from_fail(
    auth_client, company_owner, company, car_operation_factory
):
    car_operation_factory(status=CarOperation.OperationStatus.COMPLETED)

    response = auth_client(company_owner, company_id=company.id).get(
        operation_export_url(),
        {"date_from": "26-08-2026"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["message"] == "Invalid date from format"


def test_export_no_data_for_date_range_fail(
    auth_client, company_owner, company, car_operation_factory
):
    car_operation_factory(status=CarOperation.OperationStatus.COMPLETED)

    response = auth_client(company_owner, company_id=company.id).get(
        operation_export_url(),
        {"date_from": "1999-01-01", "date_to": "1999-01-02"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "لا توجد بيانات للاستخراج" in response.data["message"]


def test_export_without_company_claim_fail(auth_client, company_owner):
    response = auth_client(company_owner).get(operation_export_url())

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Branches are required" in response.data["message"]


def test_download_excel_without_authentication_fail(api_client):
    response = api_client.get(operation_download_url(), {"file": "export.xlsx"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_download_excel_forbidden_role_fail(auth_client, admin_user):
    response = auth_client(admin_user).get(
        operation_download_url(), {"file": "export.xlsx"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_download_excel_missing_file_param_fail(auth_client, company_owner, company):
    response = auth_client(company_owner, company_id=company.id).get(
        operation_download_url()
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_download_excel_unknown_file_fail(auth_client, company_owner, company):
    response = auth_client(company_owner, company_id=company.id).get(
        operation_download_url(),
        {"file": "missing.xlsx"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_download_excel_after_export_success(
    auth_client,
    company_owner,
    company,
    car_operation_factory,
    export_media_root,
):
    car_operation_factory(status=CarOperation.OperationStatus.COMPLETED)
    export_response = auth_client(company_owner, company_id=company.id).get(
        operation_export_url()
    )
    filename = parse_qs(urlparse(export_response.data["download_url"]).query)["file"][0]

    response = auth_client(company_owner, company_id=company.id).get(
        operation_download_url(),
        {"file": filename},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Disposition"] == f'attachment; filename="{filename}"'
    assert response.getvalue()
