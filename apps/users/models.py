import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django_extensions.db.models import TimeStampedModel

from apps.utilities.models.abstract_base_model import AbstractBaseModel

from .v1.managements import CustomUserManager


class User(AbstractUser, TimeStampedModel):
    username = first_name = last_name = last_login = date_joined = groups = (
        user_permissions
    ) = None

    class UserRoles(models.TextChoices):
        Admin = "admin"
        CompanyOwner = "company_owner"
        CompanyBranchManager = "company_branch_manager"
        Driver = "driver"
        StationOwner = "station_owner"
        StationBranchManager = "station_branch_manager"
        StationWorker = "station_worker"

    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=11, unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(
        max_length=25, choices=UserRoles.choices, default=UserRoles.Admin
    )
    reset_password_token = models.CharField(max_length=255, null=True, blank=True)
    reset_password_token_created_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="created_%(class)ss",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="updated_%(class)ss",
        null=True,
        blank=True,
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["name", "email"]

    def create_password_reset_token(self):
        self.reset_password_token = uuid.uuid4()
        self.reset_password_token_created_at = timezone.now()
        self.save()
        return str(self.reset_password_token)

    def is_valid_password_reset_token(self, token, expiration_hours=24):
        if self.reset_password_token and str(self.reset_password_token) == token:
            time_difference = timezone.now() - self.reset_password_token_created_at
            return time_difference.total_seconds() / 3600 < expiration_hours
        return False

    def __str__(self):
        return self.name


class FirebaseToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="firebase_tokens"
    )
    token = models.CharField(max_length=255, unique=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for {self.user.phone_number}"


class CompanyUser(User, TimeStampedModel):
    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="owners"
    )

    class Meta:
        verbose_name = "Company Owner"
        verbose_name_plural = "Company Owners"


class CompanyBranchManager(AbstractBaseModel):
    company_branch = models.ForeignKey(
        "companies.CompanyBranch", on_delete=models.CASCADE, related_name="managers"
    )
    user = models.ForeignKey(
        CompanyUser,
        on_delete=models.SET_NULL,
        related_name="company_branch_managers",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Company Branch Manager"
        verbose_name_plural = "Company Branch Managers"


class StationOwner(User):
    station = models.ForeignKey(
        "stations.Station", on_delete=models.CASCADE, related_name="owners"
    )

    class Meta:
        verbose_name = "Station Owner"
        verbose_name_plural = "Station Owners"


class StationBranchManager(User):
    station_branch = models.ForeignKey(
        "stations.StationBranch", on_delete=models.CASCADE, related_name="managers"
    )
    user = models.ForeignKey(
        StationOwner,
        on_delete=models.SET_NULL,
        related_name="station_branch_managers",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.user.name} - {self.station_branch.name}"

    class Meta:
        verbose_name = "Station Branch Manager"
        verbose_name_plural = "Station Branch Managers"


class Worker(User):
    station_branch = models.ForeignKey(
        "stations.StationBranch", on_delete=models.CASCADE, related_name="workers"
    )

    class Meta:
        verbose_name = "Worker"
        verbose_name_plural = "Workers"
