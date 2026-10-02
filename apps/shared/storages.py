import base64
import io
import json
import logging
import mimetypes
import os
import threading

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
# Drive addresses files by id. The name Django stores in the database is kept
# on the Drive file under this appProperties key so it can be looked up again.
NAME_PROPERTY = "storage_name"
DEFAULT_URL_TEMPLATE = "https://drive.google.com/uc?export=download&id={file_id}"


def build_drive_service(credentials_base64):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    info = json.loads(base64.b64decode(credentials_base64))
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=DRIVE_SCOPES
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


@deconstructible
class GoogleDriveStorage(Storage):
    """Django storage that keeps every file in one Google Drive folder.

    A service account has no Drive quota of its own, so `folder_id` must be a
    folder inside a Shared Drive the service account is a member of. With
    `public` on, each upload is shared as "anyone with the link" so `url()`
    works for the admin previews, the apps and `process_ai_operations`.
    """

    def __init__(
        self,
        credentials=None,
        folder_id=None,
        public=None,
        url_template=None,
        service=None,
    ):
        options = getattr(settings, "GOOGLE_DRIVE_STORAGE_OPTIONS", {})
        self.credentials = credentials or options.get("credentials")
        self.folder_id = folder_id or options.get("folder_id")
        self.public = options.get("public", True) if public is None else public
        self.url_template = (
            url_template or options.get("url_template") or DEFAULT_URL_TEMPLATE
        )
        self._service = service
        self._local = threading.local()
        self._ids = {}
        if not self.folder_id:
            raise ImproperlyConfigured("GOOGLE_DRIVE_FOLDER_ID is not set.")

    @property
    def service(self):
        if self._service is not None:
            return self._service
        # httplib2 is not thread-safe, so every thread gets its own client.
        if not hasattr(self._local, "service"):
            if not self.credentials:
                raise ImproperlyConfigured("GOOGLE_DRIVE_CREDENTIALS is not set.")
            self._local.service = build_drive_service(self.credentials)
        return self._local.service

    def _file_id(self, name):
        name = self._clean(name)
        if name in self._ids:
            return self._ids[name]
        escaped = name.replace("\\", "\\\\").replace("'", "\\'")
        query = (
            f"'{self.folder_id}' in parents and trashed = false and "
            f"appProperties has {{ key='{NAME_PROPERTY}' and value='{escaped}' }}"
        )
        files = (
            self.service.files()
            .list(
                q=query,
                fields="files(id)",
                pageSize=1,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
            .get("files", [])
        )
        if not files:
            return None
        self._ids[name] = files[0]["id"]
        return self._ids[name]

    @staticmethod
    def _clean(name):
        return str(name).replace("\\", "/").lstrip("/")

    def _save(self, name, content):
        from googleapiclient.http import MediaIoBaseUpload

        name = self._clean(name)
        mimetype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        if hasattr(content, "seek"):
            content.seek(0)
        media = MediaIoBaseUpload(content, mimetype=mimetype, resumable=True)
        body = {
            "name": os.path.basename(name),
            "parents": [self.folder_id],
            "appProperties": {NAME_PROPERTY: name},
        }
        created = (
            self.service.files()
            .create(body=body, media_body=media, fields="id", supportsAllDrives=True)
            .execute()
        )
        file_id = created["id"]
        if self.public:
            self.service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
                supportsAllDrives=True,
            ).execute()
        self._ids[name] = file_id
        return name

    def _open(self, name, mode="rb"):
        from googleapiclient.http import MediaIoBaseDownload

        file_id = self._file_id(name)
        if file_id is None:
            raise FileNotFoundError(name)
        buffer = io.BytesIO()
        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return File(buffer, name=name)

    def exists(self, name):
        return self._file_id(name) is not None

    def delete(self, name):
        file_id = self._file_id(name)
        if file_id is None:
            return
        self.service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        self._ids.pop(self._clean(name), None)

    def size(self, name):
        file_id = self._file_id(name)
        if file_id is None:
            raise FileNotFoundError(name)
        metadata = (
            self.service.files()
            .get(fileId=file_id, fields="size", supportsAllDrives=True)
            .execute()
        )
        return int(metadata["size"])

    def url(self, name):
        file_id = self._file_id(name)
        if file_id is None:
            # A missing file should not turn a whole list response into a 500.
            logger.warning("Google Drive file not found: %s", name)
            return ""
        return self.url_template.format(file_id=file_id)
