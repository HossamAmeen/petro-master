import os

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from apps.shared.storages import GoogleDriveStorage


class Command(BaseCommand):
    help = (
        "Upload the files in MEDIA_ROOT to Google Drive under the same names, "
        "so the paths already stored in the database keep resolving."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the files that would be uploaded without uploading them.",
        )

    def handle(self, *args, **options):
        storage = self.get_storage()
        media_root = str(settings.MEDIA_ROOT)
        uploaded = skipped = 0

        for name in self.media_names(media_root):
            if storage.exists(name):
                skipped += 1
                continue
            if options["dry_run"]:
                self.stdout.write(f"Would upload {name}")
            else:
                with open(os.path.join(media_root, name), "rb") as handle:
                    # _save keeps the exact name; save() could rename it.
                    storage._save(name, File(handle, name=name))
                self.stdout.write(f"Uploaded {name}")
            uploaded += 1

        verb = "To upload" if options["dry_run"] else "Uploaded"
        self.stdout.write(
            self.style.SUCCESS(f"{verb}: {uploaded}, already on Drive: {skipped}")
        )

    def get_storage(self):
        return GoogleDriveStorage()

    @staticmethod
    def media_names(media_root):
        for directory, _, files in sorted(os.walk(media_root)):
            for filename in sorted(files):
                path = os.path.join(directory, filename)
                yield os.path.relpath(path, media_root).replace(os.sep, "/")
