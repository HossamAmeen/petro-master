from django.db import models

from apps.utilities.models.abstract_base_model import AbstractBaseModel


class KhaznaTransaction(AbstractBaseModel):
    class TransactionStatus(models.TextChoices):
        PENDING = "pending", ("Pending")
        APPROVED = "approved", ("Approved")
        DECLINED = "declined", ("Declined")

    class TransactionMethod(models.TextChoices):
        BANK = "bank", ("Bank")
        INSTAPAY = "instapay", ("Instapay")
        CASH = "cash", ("Cash")
        WALLET = "wallet", ("Wallet")

    is_incoming = models.BooleanField(
        help_text="True if money came into the khazna;" "False if it went out."
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
    )
    reviewed_by = models.JSONField(default=list, blank=True)
    reference_code = models.CharField(
        max_length=100, unique=True, help_text="If there was invoice or receipt code"
    )
    description = models.TextField(null=True, blank=True)
    method = models.CharField(
        max_length=20, choices=TransactionMethod.choices, default=TransactionMethod.CASH
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    photo = models.ImageField(
        upload_to="kazna_transaction_photos/", null=True, blank=True
    )
    is_unpaid = models.BooleanField(
        default=False, help_text="True if the transaction hasn't been paid yet."
    )
    is_internal = models.BooleanField(
        default=False, help_text="True if the transaction is internal."
    )

    def __str__(self):
        return f"{'IN' if self.is_incoming else 'OUT'} | {self.amount} | {self.reference_code}"  # noqa


class CompanyKhaznaTransaction(KhaznaTransaction):
    class ForWhat(models.TextChoices):
        BRANCH = "Branch"
        CAR = "Car"

    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE)
    for_what = models.CharField(
        max_length=20,
        choices=ForWhat.choices,
        default=ForWhat.BRANCH,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{'IN' if self.is_incoming else 'OUT'} | {self.amount} | {self.reference_code}"  # noqa

    class Meta:
        verbose_name = "Company Khazna Transaction"
        verbose_name_plural = "Company Khazna Transactions"


class StationKhaznaTransaction(KhaznaTransaction):
    station = models.ForeignKey("stations.Station", on_delete=models.CASCADE)

    def __str__(self):
        return f"{'IN' if self.is_incoming else 'OUT'} | {self.amount} | {self.reference_code}"  # noqa

    class Meta:
        verbose_name = "Station Khazna Transaction"
        verbose_name_plural = "Station Khazna Transactions"
