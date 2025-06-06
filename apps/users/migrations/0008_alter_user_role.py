# Generated by Django 4.2 on 2025-05-08 06:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_alter_worker_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Admin"),
                    ("company_owner", "Companyowner"),
                    ("company_branch_manager", "Companybranchmanager"),
                    ("driver", "Driver"),
                    ("station_owner", "Stationmanager"),
                    ("station_branch_manager", "Stationemployee"),
                    ("station_worker", "Stationworker"),
                ],
                default="admin",
                max_length=25,
            ),
        ),
    ]
