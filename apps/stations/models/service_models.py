from django.db import models

from apps.utilities.models.abstract_base_model import AbstractBaseModel


class Service(AbstractBaseModel):
    class ServiceType(models.TextChoices):
        PETROL = "petrol"
        DIESEL = "diesel"
        WASH = "wash"
        OTHER = "other"

    class ServiceUnit(models.TextChoices):
        LITRE = "litre"
        UNIT = "unit"
        OTHER = "other"

    name = models.CharField(max_length=25)
    unit = models.CharField(
        max_length=20, choices=ServiceUnit.choices, default=ServiceUnit.OTHER
    )
    type = models.CharField(
        max_length=25, choices=ServiceType.choices, default=ServiceType.OTHER
    )
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    image = models.ImageField(upload_to="service_images/", null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
