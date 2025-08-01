# Generated by Django 4.2 on 2025-07-04 13:35

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0005_alter_car_fuel_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="companycashrequest",
            name="company_cost",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.AddField(
            model_name="companycashrequest",
            name="station_cost",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
    ]
