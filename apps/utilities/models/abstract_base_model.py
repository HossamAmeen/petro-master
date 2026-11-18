from django.db import models, transaction
from django.utils import timezone
from django_extensions.db.models import TimeStampedModel


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """Soft delete every row in the queryset."""
        if self.model.soft_delete_related is AbstractBaseModel.soft_delete_related:
            return self.update(deleted_at=timezone.now())
        # The model cascades to related rows, so delete row by row.
        with transaction.atomic(using=self.db):
            rows = list(self)
            for row in rows:
                row.delete()
        return len(rows)

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Default manager: returns only rows that are not soft deleted."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Returns every row, including soft deleted ones."""


class AbstractBaseModel(TimeStampedModel):
    created_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT, related_name="created_%(class)ss"
    )
    updated_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="updated_%(class)ss",
        null=True,
        blank=True,
    )
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete: stamp deleted_at instead of removing the row."""
        with transaction.atomic(using=using):
            self.deleted_at = timezone.now()
            self.save(using=using, update_fields=["deleted_at"])
            self.soft_delete_related(self.deleted_at)

    def soft_delete_related(self, deleted_at):
        """Hook for models whose related rows must be soft deleted with them.

        Rows already deleted keep their own `deleted_at`.
        """

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self):
        return self.deleted_at is not None
