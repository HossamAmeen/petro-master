from unittest.mock import patch

from apps.companies.helper import upload_export

HOOK = "apps.companies.tests.test_upload_export.fake_upload"


def fake_upload(filepath, filename):
    return f"uploaded:{filename}"


def failing_upload(filepath, filename):
    raise RuntimeError("drive down")


class TestUploadExport:

    def test_unset_setting_does_nothing(self, settings):
        settings.EXPORT_UPLOAD_FUNCTION = None

        assert upload_export("/tmp/a.xlsx", "a.xlsx") is None

    def test_calls_configured_function(self, settings):
        settings.EXPORT_UPLOAD_FUNCTION = HOOK

        assert upload_export("/tmp/a.xlsx", "a.xlsx") == "uploaded:a.xlsx"

    def test_failure_is_swallowed(self, settings):
        settings.EXPORT_UPLOAD_FUNCTION = (
            "apps.companies.tests.test_upload_export.failing_upload"
        )

        with patch("apps.companies.helper.logger") as logger:
            assert upload_export("/tmp/a.xlsx", "a.xlsx") is None

        logger.exception.assert_called_once()
