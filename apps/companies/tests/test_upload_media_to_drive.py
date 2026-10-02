from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage
from django.core.management import call_command


class TestUploadMediaToDrive:

    @pytest.fixture(autouse=True)
    def setup(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        (tmp_path / "fuel_images").mkdir()
        (tmp_path / "fuel_images" / "a.png").write_bytes(b"new")
        (tmp_path / "old.png").write_bytes(b"old")
        self.drive = InMemoryStorage()
        self.drive.save("old.png", ContentFile(b"old"))
        patcher = patch(
            "apps.companies.management.commands.upload_media_to_drive"
            ".Command.get_storage",
            return_value=self.drive,
        )
        patcher.start()
        yield
        patcher.stop()

    def test_uploads_missing_files_under_same_name_success(self, capsys):
        call_command("upload_media_to_drive")

        with self.drive.open("fuel_images/a.png") as handle:
            assert handle.read() == b"new"
        assert "Uploaded: 1, already on Drive: 1" in capsys.readouterr().out

    def test_dry_run_uploads_nothing_success(self, capsys):
        call_command("upload_media_to_drive", "--dry-run")

        assert not self.drive.exists("fuel_images/a.png")
        output = capsys.readouterr().out
        assert "Would upload fuel_images/a.png" in output
        assert "To upload: 1, already on Drive: 1" in output
