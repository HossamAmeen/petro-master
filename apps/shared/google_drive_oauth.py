import logging
import mimetypes

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_URI = "https://oauth2.googleapis.com/token"
DEFAULT_URL_TEMPLATE = "https://drive.google.com/uc?export=download&id={file_id}"


def build_drive_service():
    """Drive v3 client acting as the Google account that granted the refresh token."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    options = settings.GOOGLE_DRIVE_OAUTH_OPTIONS
    missing = [
        key
        for key in ("client_id", "client_secret", "refresh_token")
        if not options.get(key)
    ]
    if missing:
        raise ImproperlyConfigured(
            "Missing GOOGLE_DRIVE_OAUTH_* settings: " + ", ".join(missing)
        )
    credentials = Credentials(
        token=None,
        refresh_token=options["refresh_token"],
        client_id=options["client_id"],
        client_secret=options["client_secret"],
        token_uri=TOKEN_URI,
        scopes=DRIVE_SCOPES,
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def upload_to_drive(filepath, filename, service=None):
    """Upload a local file to Google Drive with OAuth; return its link.

    Meant for `settings.EXPORT_UPLOAD_FUNCTION`. It uses the account's own
    quota, so the folder can be any My Drive folder.
    """
    from googleapiclient.http import MediaFileUpload

    options = settings.GOOGLE_DRIVE_OAUTH_OPTIONS
    service = service or build_drive_service()
    body = {"name": filename}
    if options.get("folder_id"):
        body["parents"] = [options["folder_id"]]
    mimetype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    created = (
        service.files()
        .create(
            body=body,
            media_body=MediaFileUpload(filepath, mimetype=mimetype),
            fields="id",
        )
        .execute()
    )
    file_id = created["id"]
    if options.get("public"):
        service.permissions().create(
            fileId=file_id, body={"type": "anyone", "role": "reader"}
        ).execute()
    template = options.get("url_template") or DEFAULT_URL_TEMPLATE
    return template.format(file_id=file_id)
