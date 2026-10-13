from unittest.mock import MagicMock

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.shared.google_drive_oauth import build_drive_service, upload_to_drive


@pytest.fixture
def service():
    service = MagicMock()
    service.files.return_value.create.return_value.execute.return_value = {"id": "abc"}
    return service


@pytest.fixture
def xlsx(tmp_path):
    path = tmp_path / "export.xlsx"
    path.write_bytes(b"data")
    return str(path)


class TestUploadToDrive:

    def test_upload_returns_download_link(self, settings, service, xlsx):
        settings.GOOGLE_DRIVE_OAUTH_OPTIONS = {"folder_id": "folder"}

        url = upload_to_drive(xlsx, "export.xlsx", service=service)

        body = service.files.return_value.create.call_args.kwargs["body"]
        assert body == {"name": "export.xlsx", "parents": ["folder"]}
        assert url == "https://drive.google.com/uc?export=download&id=abc"
        service.permissions.assert_not_called()

    def test_public_shares_file_with_link(self, settings, service, xlsx):
        settings.GOOGLE_DRIVE_OAUTH_OPTIONS = {"public": True}

        upload_to_drive(xlsx, "export.xlsx", service=service)

        body = service.permissions.return_value.create.call_args.kwargs["body"]
        assert body == {"type": "anyone", "role": "reader"}
        created = service.files.return_value.create.call_args.kwargs["body"]
        assert "parents" not in created

    def test_custom_url_template(self, settings, service, xlsx):
        settings.GOOGLE_DRIVE_OAUTH_OPTIONS = {"url_template": "https://x/{file_id}"}

        assert upload_to_drive(xlsx, "export.xlsx", service=service) == "https://x/abc"

    def test_missing_credentials_fail(self, settings):
        settings.GOOGLE_DRIVE_OAUTH_OPTIONS = {"client_id": "id"}

        with pytest.raises(ImproperlyConfigured):
            build_drive_service()
