# Generated by Django 4.2 on 2025-05-05 14:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0012_alter_companybranch_company"),
    ]

    operations = [
        migrations.AddField(
            model_name="car",
            name="oil_type",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
