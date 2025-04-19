# Generated by Django 4.2 on 2025-04-19 17:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("geo", "0001_initial"),
        ("stations", "0003_alter_service_updated_by_alter_station_updated_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="stationbranch",
            name="district",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="geo.district",
            ),
        ),
        migrations.AddField(
            model_name="stationbranch",
            name="lang",
            field=models.FloatField(default=None),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="stationbranch",
            name="lat",
            field=models.FloatField(default=None),
            preserve_default=False,
        ),
    ]
