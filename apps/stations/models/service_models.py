import imghdr
import mimetypes

from django.core.exceptions import ValidationError
from django.db import models

from apps.utilities.models.abstract_base_model import AbstractBaseModel


def validate_image_or_svg(file):
    mime_type, _ = mimetypes.guess_type(file.name)
    if mime_type == "image/svg+xml":
        return  # Allow SVGs
    elif imghdr.what(file) in ["jpeg", "png", "gif"]:
        return  # Allow raster images
    raise ValidationError("Only valid images or SVGs are allowed.")


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
    image = models.FileField(
        upload_to="service_images/",
        null=True,
        blank=True,
        validators=[validate_image_or_svg],
    )

    def __str__(self):
        return self.name

    def get_unit_display(self):
        return self.unit + "+"

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
