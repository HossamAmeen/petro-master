from django.contrib.auth.models import AbstractUser
from django.db import models
from django_extensions.db.models import TimeStampedModel

from .v1.managements import CustomUserManager


class UserRoles(models.TextChoices):
    Admin = 'admin'
    CompanyOwner = 'company_owner'
    BranchManager = 'branch_manager'
    Driver = 'driver'
    StationManager = 'station_manager'
    StationEmployee = 'station_employee'
    StationWorker = 'station_worker'


class User(AbstractUser, TimeStampedModel):
    username = first_name = last_name = last_login = date_joined = groups = user_permissions = None
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=11, unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=25, choices=UserRoles.choices, default=UserRoles.Admin)
    created_by = models.ForeignKey('self', on_delete=models.CASCADE, related_name="created_%(class)ss", null=True, blank=True)
    updated_by = models.ForeignKey('self', on_delete=models.CASCADE, related_name="updated_%(class)ss", null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["name", 'email']

    def __str__(self):
        return self.name
