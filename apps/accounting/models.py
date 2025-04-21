from django.db import models
from django_extensions.db.models import TimeStampedModel
from polymorphic.models import PolymorphicModel


class KhaznaTransaction(TimeStampedModel, PolymorphicModel):
    class TransactionStatus(models.TextChoices):
        PENDING = 'pending', ('Pending')
        APPROVED = 'approved', ('Approved')
        DECLINED = 'declined', ('Declined')

    class TransactionMethod(models.TextChoices):
        BANK = 'bank', ('Bank')
        INSTAPAY = 'instapay', ('Instapay')
        CASH = 'cash', ('Cash')

    is_incoming = models.BooleanField(help_text="True if money came into the khazna; False if it went out.")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING
    )
    reviewed_by = models.JSONField(default=list, blank=True)
    reference_code = models.CharField(max_length=100, unique=True,
                                      help_text="If there was invoice or receipt code")
    description = models.TextField(null=True, blank=True)
    method = models.CharField(
        max_length=20,
        choices=TransactionMethod.choices,
        default=TransactionMethod.CASH
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{'IN' if self.is_incoming else 'OUT'} | {self.amount} | {self.reference_code}"
