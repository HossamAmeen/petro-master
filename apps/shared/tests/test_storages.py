from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile

from apps.shared.storages import NAME_PROPERTY, GoogleDriveStorage


def drive_service(listed=None):
    """A Drive v3 client whose `files().list` returns the given file ids."""
    service = MagicMock()
    files = service.files.return_value
    files.list.return_value.execute.return_value = {
        "files": [{"id": file_id} for file_id in (listed or [])]
    }
    files.create.return_value.execute.return_value = {"id": "new-id"}
    files.get.return_value.execute.return_value = {"size": "42"}
    return service


class TestGoogleDriveStorage:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = drive_service()
        self.files = self.service.files.return_value
        self.storage = GoogleDriveStorage(folder_id="folder", service=self.service)

    def test_missing_folder_id_fail(self, settings):
        settings.GOOGLE_DRIVE_STORAGE_OPTIONS = {}

        with pytest.raises(ImproperlyConfigured):
            GoogleDriveStorage(service=self.service)

    def test_missing_credentials_fail(self, settings):
        settings.GOOGLE_DRIVE_STORAGE_OPTIONS = {"folder_id": "folder"}

        with pytest.raises(ImproperlyConfigured):
            GoogleDriveStorage().exists("a.png")

    def test_options_read_from_settings_success(self, settings):
        settings.GOOGLE_DRIVE_STORAGE_OPTIONS = {
            "credentials": "creds",
            "folder_id": "folder",
            "public": False,
            "url_template": "https://files.test/{file_id}",
        }

        storage = GoogleDriveStorage()

        assert storage.credentials == "creds"
        assert storage.folder_id == "folder"
        assert storage.public is False
        assert storage.url_template == "https://files.test/{file_id}"

    @patch("apps.shared.storages.build_drive_service")
    def test_service_built_once_from_credentials_success(self, build, settings):
        settings.GOOGLE_DRIVE_STORAGE_OPTIONS = {
            "credentials": "creds",
            "folder_id": "folder",
        }
        storage = GoogleDriveStorage()

        assert storage.service is storage.service
        build.assert_called_once_with("creds")

    def test_save_uploads_into_folder_and_shares_success(self):
        name = self.storage.save("fuel_images/photo.png", ContentFile(b"png"))

        assert name == "fuel_images/photo.png"
        body = self.files.create.call_args.kwargs["body"]
        assert body == {
            "name": "photo.png",
            "parents": ["folder"],
            "appProperties": {NAME_PROPERTY: "fuel_images/photo.png"},
        }
        self.service.permissions.return_value.create.assert_called_once_with(
            fileId="new-id",
            body={"type": "anyone", "role": "reader"},
            supportsAllDrives=True,
        )
        # The id is remembered, so the URL needs no further lookup.
        self.files.list.reset_mock()
        assert (
            self.storage.url(name)
            == "https://drive.google.com/uc?export=download&id=new-id"
        )
        self.files.list.assert_not_called()

    def test_save_private_does_not_share_success(self):
        storage = GoogleDriveStorage(
            folder_id="folder", public=False, service=self.service
        )

        storage.save("a.png", ContentFile(b"png"))

        self.service.permissions.return_value.create.assert_not_called()

    def test_save_existing_name_gets_new_name_success(self):
        self.files.list.return_value.execute.side_effect = [
            {"files": [{"id": "taken"}]},
            {"files": []},
        ]

        name = self.storage.save("a.png", ContentFile(b"png"))

        assert name != "a.png"
        assert name.startswith("a_") and name.endswith(".png")

    def test_exists_looks_up_stored_name_success(self):
        self.files.list.return_value.execute.return_value = {"files": [{"id": "x"}]}

        assert self.storage.exists("service_images/it's.png")

        query = self.files.list.call_args.kwargs["q"]
        assert "'folder' in parents" in query
        assert f"key='{NAME_PROPERTY}' and value='service_images/it\\'s.png'" in query

    def test_exists_unknown_name_fail(self):
        assert not self.storage.exists("missing.png")

    def test_open_downloads_content_success(self):
        self.files.list.return_value.execute.return_value = {"files": [{"id": "x"}]}

        def fake_downloader(buffer, request):
            buffer.write(b"content")
            downloader = MagicMock()
            downloader.next_chunk.return_value = (None, True)
            return downloader

        with patch("googleapiclient.http.MediaIoBaseDownload", fake_downloader):
            with self.storage.open("a.xlsx") as handle:
                assert handle.read() == b"content"

        self.files.get_media.assert_called_once_with(fileId="x", supportsAllDrives=True)

    def test_open_unknown_name_fail(self):
        with pytest.raises(FileNotFoundError):
            self.storage.open("missing.xlsx")

    def test_size_success(self):
        self.files.list.return_value.execute.return_value = {"files": [{"id": "x"}]}

        assert self.storage.size("a.png") == 42

    def test_size_unknown_name_fail(self):
        with pytest.raises(FileNotFoundError):
            self.storage.size("missing.png")

    def test_delete_removes_file_and_cached_id_success(self):
        self.storage.save("a.png", ContentFile(b"png"))

        self.storage.delete("a.png")

        self.files.delete.assert_called_once_with(
            fileId="new-id", supportsAllDrives=True
        )
        assert not self.storage.exists("a.png")

    def test_delete_unknown_name_fail(self):
        self.storage.delete("missing.png")

        self.files.delete.assert_not_called()

    def test_url_unknown_name_fail(self, caplog):
        with caplog.at_level("WARNING", logger="apps.shared.storages"):
            assert self.storage.url("missing.png") == ""

        assert "missing.png" in caplog.text
