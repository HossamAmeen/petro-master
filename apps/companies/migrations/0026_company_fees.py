# Generated by Django 4.2 on 2025-06-11 08:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0025_alter_caroperation_amount_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="fees",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=5),
        ),
    ]
