# Generated by Django 4.2 on 2025-06-25 16:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="stationbranch",
            name="cash_request_fees",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=5),
        ),
        migrations.AddField(
            model_name="stationbranch",
            name="other_service_fees",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=5),
        ),
        migrations.RemoveField(
            model_name="station",
            name="fees",
        ),
    ]
