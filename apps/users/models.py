from django.db import models
from django.contrib.auth.models import  AbstractUser
from .managements import CustomUserManager


class User(AbstractUser):
    username = first_name = last_name = groups = user_permissions = None
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=11, unique=True)
    password = models.CharField(max_length=255)

    objects = CustomUserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["name", 'email']

    def __str__(self):
        return self.phone_number
